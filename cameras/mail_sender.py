import smtplib
import imghdr
from email.message import EmailMessage

class mail_sender():

    Sender_Email = "*"
    Receiver_Email = "*"
    Password = '*'
    newMessage = None

    def __init__(self, sender_email : str, password : str, receiver_email : str):
        self.Sender_Email = sender_email
        self.Receiver_Email = receiver_email
        self.Password = password

    def send(self, subject : str, content : str, url_image = None):

        self.newMessage = EmailMessage()                         
        self.newMessage['Subject'] = subject 
        self.newMessage['From'] = self.Sender_Email                   
        self.newMessage['To'] = self.Receiver_Email                   
        self.newMessage.set_content(content)

        if url_image is not None:
            with open(url_image, 'rb') as f:
                image_data = f.read()
                image_type = imghdr.what(f.name)
                image_name = f.name
            self.newMessage.add_attachment(image_data, maintype='image', subtype=image_type, filename=image_name)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(self.Sender_Email, self.Password)              
            smtp.send_message(self.newMessage)