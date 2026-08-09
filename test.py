import imaplib
import email

imap_server = "imap.gmail.com"
imap = imaplib.IMAP4_SSL(imap_server)
email = "benxdonx@gmail.com"
pw = "tpvw gmoh wwga aawg"

imap.login(email, pw)
