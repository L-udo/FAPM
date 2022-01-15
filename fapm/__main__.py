import os
import sys

import jinja2
from werkzeug.utils import secure_filename

from . import cli
from . import db
from . import download
from . import query


ABOUT_LOG_OUT = """
For your security, you should log out of your FurAffinity account. This will
invalidate the session cookies you provided to this script.
""".rstrip()


def noun(count, singular, plural):
    return f'{count:,} {singular if count == 1 else plural}'


db.Model.metadata.create_all()

if cli.args.update:
    download.prompt_session_tokens()
    new_message_index = download.message_index()
    old_message_index = query.message_index()
    moved_messages = {id_: folder for id_, folder in new_message_index.items() if id_ in old_message_index and old_message_index[id_] != folder}
    unsaved_messages = {id_: folder for id_, folder in new_message_index.items() if id_ not in old_message_index}

    if moved_messages:
        print(f'Updating {noun(len(moved_messages), "message", "messages")} moved to another folder')

        for id_, folder in moved_messages.items():
            query.move_message(id_, folder)

    if unsaved_messages:
        print(f'Found {noun(len(unsaved_messages), "message", "messages")} not in database')

        with db.Session() as session:
            for id_, folder in unsaved_messages.items():
                message = download.get_message(id_, folder)
                print(f'Downloaded message [{message.timestamp_format()}] {message.subject or "No Subject"}')
                session.add(message)

            session.commit()
            print('Finished downloading messages')

    else:
        print('No new messages to download')

jinja_loader = jinja2.FileSystemLoader('templates')
jinja_env = jinja2.Environment(loader=jinja_loader, autoescape=True)
jinja_env.globals.update(secure_filename=secure_filename)
index_template = jinja_env.get_template('index.html')
conversation_template = jinja_env.get_template('conversation.html')

try:
    os.mkdir('html')
except OSError:
    pass

contacts = query.contacts()
messages_for_index = []

if not contacts:
    sys.exit('No conversations to format')

print(f'Formatting conversations with {noun(len(contacts), "contact", "contacts")}')

for contact in contacts:
    messages = query.conversation(contact)
    messages_for_index.append(messages[-1])

    with open(f'html/{secure_filename(contact)}.html', 'w') as file_:
        file_.write(conversation_template.render(contact=contact, messages=messages))

with open('index.html', 'w') as file_:
    file_.write(index_template.render(messages=messages_for_index))

if cli.args.update:
    print(ABOUT_LOG_OUT)
