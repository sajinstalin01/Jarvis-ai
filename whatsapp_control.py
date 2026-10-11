"""WhatsApp Web helper. Contact/message selection is explicit and sending requires confirmation."""
import re, webbrowser
from urllib.parse import quote

def open_whatsapp():
    webbrowser.open("https://web.whatsapp.com/")
    return "WhatsApp Web opened. Use the in-app search bar to find the exact contact."

def search_contact(name):
    name=name.strip()
    if not name: return "Tell me the contact name to search for."
    webbrowser.open("https://web.whatsapp.com/")
    return f"WhatsApp Web opened. Search for '{name}' in WhatsApp's own search bar and verify the exact person before messaging. This helper does not read your private contacts."

def prepare_message(contact, message):
    contact=contact.strip(); message=message.strip()
    if not contact or not message: return "Usage: whatsapp message <contact name> | <message>"
    # Contact names cannot be resolved reliably via a public URL; never guess a recipient.
    return ("Draft prepared, not sent. Open WhatsApp Web, search for the exact contact "
            f"'{contact}', verify the recipient, then paste this message:\n\n{message}\n\n"
            "For direct wa.me links, use a verified international phone number and ask for confirmation first.")

def open_number_chat(number, message=""):
    digits=re.sub(r"\\D","",number)
    if len(digits)<8 or len(digits)>15: return False,"Use a verified international phone number including country code."
    url="https://wa.me/"+digits
    if message: url+="?text="+quote(message)
    webbrowser.open(url)
    return True,"Opened a WhatsApp draft link. Review recipient and message, then press Send yourself."
