# TODO
## Fetch email from gmail using gmail api  
## 

# Import necessary libraries 
# 导入必要的库
import os.path
from pyexpat.errors import messages
from time import process_time_ns

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from google.oauth2 import service_account

# for encoding/decoding messages in base64
import base64

# for dealing with attachement MIME types
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from mimetypes import guess_type as guess_mime_type


# Get the current file's directory path
current_dir = os.path.dirname(__file__)

# Define the relative path of credentials.json file
credentials_path = os.path.join(current_dir, "..", "..", "credentials.json")

# Define the relative path of token.json file
token_path = os.path.join(current_dir, "..", "..", "token.json")

temp_path = os.path.join(current_dir, "..", "..", "temp")

fetcher_temp_path = os.path.join(temp_path, "mails")




# SCOPE 
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]




def authenticate():
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
            credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
        with open(token_path, "w") as token:
            token.write(creds.to_json())
    return build(
        "gmail", "v1", credentials=creds
        )

# NOTE For query, we can use Gmail search operators like from:, subject:, and more. See https://support.google.com/mail/answer/7190 for for imformation.  
def search_messages(service, user_id, query):
    # Use the Gmail API to search for messages
    # 使用 Gmail API 搜索消息
    result = service.users().messages().list(userId=user_id, q=query).execute()
    messages = []
    if "messages" in result:
        messages.extend(result["messages"])
    # Handle pagination results
    # 处理分页结果
    while "nextPageToken" in result:
        page_token = result["nextPageToken"]
        result = (
            service.users()
            .messages()
            .list(userId=user_id, q=query, pageToken=page_token)
            .execute()
        )
        if "messages" in result:
            messages.extend(result["messages"])
    return messages

def get_size_format(b, factor=1024, suffix="B"):
    """
    Scale bytes to its proper byte format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if b < factor:
            return f"{b:.2f}{unit}{suffix}"
        b /= factor
    return f"{b:.2f}Y{suffix}"

def clean(text):
    # clean text for creating a folder
    return "".join(c if c.isalnum() else "_" for c in text)



def parse_parts(service, user_id, parts, folder_name, message):
    """
    Parse the conntent of an email partition
    """
    if not parts:
        return print("No parts found in message")
    else:
        for part in parts:
            filename = part.get("filename")
            mimeType = part.get("mimeType")
            body = part.get("body")
            data = body.get("data")
            size = body.get("size")
            part_headers = part.get("headers")
            if part.get("parts"):
                # recursively call this function when we see that a part
                # has parts inside
                parse_parts(service, user_id, part.get("parts"), folder_name, message)
            if mimeType == "text/plain":
                if data:
                    text = base64.urlsafe_b64decode(data).decode()
                    print(text)
            elif mimeType == "text/html":
                if not filename:
                    # creat dir for every html
                    # filename = "index.html"
                    filename = folder_name + ".html"
                    filepath = os.path.join(fetcher_temp_path, folder_name, filename)
                    print("Saving HTML to", filepath)
                    with open(filepath, "wb+") as f:
                        f.write(base64.urlsafe_b64decode(data))
            else:
                for part_header in part_headers:
                    part_header_name = part_header.get("name")
                    part_header_value = part_header.get("value")
                    if part_header_name == "Content-Disposition":
                        if "attachment" in part_header_value:
                            # we got an attachment
                            print("Attachment:", filename)
                            print("Attachment Size:", get_size_format(size))
                            attachment_id = body.get("attachmentId")
                            attachment = service.users() \
                            .messages() \
                            .attachments() \
                            .get(id = attachment_id, userId = user_id, messageId = message["id"]) \
                            .execute()
                            data = attachment.get("data")
                            filepath = os.path.join(fetcher_temp_path, folder_name, filename)
                            if data:
                                with open(filepath, "wb") as f:
                                    f.write(base64.urlsafe_b64decode(data))


def read_message(service, user_id, msg_id):
    """
    Get a message from its id
    """
    message = service.users().messages().get(userId=user_id, id=msg_id['id'], format="full").execute()
    payload = message["payload"]
    headers = payload.get("headers")
    parts = payload.get("parts")
    folder_name = "INBOX"
    is_subjected = False
    if headers:
        for header in headers:
            name = header.get("name")
            value = header.get("value")
            
            if name.lower() == "from":
                # From somewhere
                print("From:", value)
            
            if name.lower() == "to":
                # To someone
                print("To:", value)
            
            if name.lower() == "subject":
                # The subject
                is_subjected = True
                folder_name = clean(value)
                folder_counter = 0
                while os.path.isdir(os.path.join(fetcher_temp_path, folder_name)):
                    folder_counter += 1
                    
                    if folder_name[-1].isdigit() and folder_name[-2] == "_":
                        folder_name = f"{folder_name[:-2]}_{folder_counter}"
                    
                    elif folder_name[-2:].isdigit() and folder_name[-3] == "_":
                        folder_name = f"{folder_name[:-3]}_{folder_counter}"
                    
                    else:
                        folder_name = f"{folder_name}_{folder_counter}"

                os.mkdir(os.path.join(fetcher_temp_path, folder_name))
                print("Subject:", value)
                
            if name.lower() == "date":
                # The date when the message was sent
                print("Date:", value)

    if not is_subjected:
        if not os.path.isdir(os.path.join(fetcher_temp_path, folder_name)):
            os.mkdir(os.path.join(fetcher_temp_path, folder_name))

    parse_parts(service, user_id, parts, folder_name, message)
    print("="*55)


# TODO 
from ..utils.clean_duplicate_mails import delete_duplicate_mails

def gmail_fetch(user_id, query, service=None):
    # TODO for multiple users

    # TEST 
    # user_id = "me"
    # query = "newer_than:1d"
    # query = "eCHO"


    try:
        if service is None:
            service = authenticate()

        # # Call the Gmail API
        # results = service.users().labels().list(userId = user_id).execute()
        # labels = results.get("labels", [])
        # if not labels:
        #     print("No labels found.")
        #     return 
        # print("Labels:")
        # for label in labels:
        #     print(label["name"])

        results = search_messages(service, user_id, query)
        print(f"Found {len(results)} results.")

        for message in results:
            read_message(service, user_id, message)

        delete_duplicate_mails(fetcher_temp_path)


    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f"An error occurred: {error}")



if __name__ == "__main__":
    gmail_fetch(user_id="me", query='("job alert" OR "medium" OR "联合早报" OR "eCHO") newer_than:3d')