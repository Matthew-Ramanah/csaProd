from pyConfig import *

__version__ = "0.0.2"
SCOPES = 'https://www.googleapis.com/auth/gmail.readonly'
CSV_MIME_TYPE = 'text/csv'
XLSX_MIME_TYPES = ['application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']


def mime_type_to_dtype(s):
    if s == CSV_MIME_TYPE:
        return 'csv'
    if s in XLSX_MIME_TYPES:
        return 'xlsx'
    raise AssertionError("mime type not accepted")


def get_gmail_service(credentials_path, token_path):
    store = file.Storage(token_path)
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets(credentials_path, SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('gmail', 'v1', http=creds.authorize(Http()), cache_discovery=False)
    return service.users()


def query_for_message_ids(service, search_query):
    """searching for an e-mail (Supports the same query format as the Gmail search box.
    For example, "from:someuser@example.com rfc822msgid:<somemsgid@example.com>
    is:unread")
    """
    result = service.messages().list(userId='me', q=search_query).execute()
    results = result.get('messages')
    if results:
        msg_ids = [r['id'] for r in results]
    else:
        msg_ids = []

    return msg_ids


def _get_attachment_data(service, messageId, attachmentId):
    att = service.messages().attachments().get(
        userId='me', id=attachmentId, messageId=messageId).execute()
    return att['data']


def _get_attachment_from_part(service, messageId, part):
    body = part.get('body')
    data = body.get('data')
    attachmentId = body.get('attachmentId')
    if data:
        return data
    if attachmentId:
        return _get_attachment_data(service, messageId, attachmentId)


def _convert_attachment_data_to_dataframe(data, data_type):
    str_decoded = base64.urlsafe_b64decode(data.encode('UTF-8'))
    if data_type == 'csv':
        df = pd.read_csv(BytesIO(str_decoded))
    elif data_type == 'xlsx':
        df = pd.read_excel(BytesIO(str_decoded))
    return df


def _findAttPart(msg_parts, fileQuery):
    for p in msg_parts:
        if fileQuery in p['filename']:
            return p
    return None


def pullLatestPosFile(service, searchQuery, fileQuery):
    message_ids = query_for_message_ids(service, searchQuery)
    for messageId in message_ids:
        msg = service.messages().get(userId='me', id=messageId).execute()
        msg_parts = msg.get('payload').get('parts')
        headers = msg.get('payload').get('headers')
        subject = [h['value'] for h in headers if h['name'] == 'Subject'][0]
        if not msg_parts:
            continue
        attPart = _findAttPart(msg_parts, fileQuery)
        if attPart is None:
            continue
        attType = mime_type_to_dtype(attPart['mimeType'])
        data = _get_attachment_from_part(service, messageId, attPart)
        df = _convert_attachment_data_to_dataframe(data, attType)
        return {'emailsubject': subject, 'filename': attPart['filename'], 'data': df}


def sendFile(path, sendFrom, sendTo, sendCC, username, password, subject, message, filename):
    msg = MIMEMultipart()
    msg['From'] = sendFrom
    msg['To'] = ", ".join(sendTo)
    msg['Cc'] = ", ".join(sendCC)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach(MIMEText(message))

    part = MIMEBase('application', "octet-stream")
    with open(path, 'rb') as file:
        part.set_payload(file.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename={filename}')
        msg.attach(part)

    smtp = smtplib.SMTP(host="smtp.gmail.com", port=587)
    smtp.ehlo()
    smtp.starttls()
    smtp.login(username, password)
    smtp.sendmail(sendFrom, sendTo + sendCC, msg.as_string())
    smtp.quit()
    return


def sendSummaryFiles(paths, sendFrom, sendTo, sendCC, username, password, subject, message):
    msg = MIMEMultipart()
    msg['From'] = sendFrom
    msg['To'] = ", ".join(sendTo)
    msg['Cc'] = ", ".join(sendCC)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach(MIMEText(message))

    for investor in paths:
        attachment = MIMEApplication(open(paths[investor], "rb").read(), _subtype="txt")
        attachment.add_header('Content-Disposition', 'attachment', filename=f'{investor}.csv')
        msg.attach(attachment)

    smtp = smtplib.SMTP(host="smtp.gmail.com", port=587)
    smtp.ehlo()
    smtp.starttls()
    smtp.login(username, password)
    smtp.sendmail(sendFrom, sendTo + sendCC, msg.as_string())
    smtp.quit()
    lg.info("Sent Summary Email")
    return
