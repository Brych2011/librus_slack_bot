import json
import os
import time

from librus_api.api import Librus, Message, Notice
from slackclient import SlackClient
import datetime

CHANNEL = "bot_testing_ground"
ARCHIVE_PATH = "archive/"
MESSAGE_CHANNEL_MAP = {
    "do klasy": "bot_testing_ground",
    "chemia": "bot_testing_ground",
    "laboratorium": "bot_testing_ground"
}


def archive_notice(notice: Notice):
    fname = datetime.datetime.now().strftime("%Y-%m-%d") + "_" + notice.subject
    if os.path.exists(ARCHIVE_PATH + fname):
        i = 2
        while os.path.exists(ARCHIVE_PATH + fname + str(i)):
            i += 1
        fname = ARCHIVE_PATH + fname + str(i)

    with open(fname, 'w') as file:
        file.write(notice.subject)
        file.write("\n\n")
        file.write(notice.content)
        file.write(f"\n\n Author: {notice.teacher.first_name} {notice.teacher.last_name}")


def archive_lucky_number(number):
    with open(ARCHIVE_PATH + "LuckyNumbers", 'a') as file:
        file.write(f"{datetime.datetime.now().strftime('%Y-%m-%d')}: {number}\n")


def message_flow(librus_api: Librus, slack_api: SlackClient, channel_map: dict, last_message: datetime.datetime):
    """Full message flow: fetching from librus, filtering and posting
    :returns datetime object of last message parsed"""

    page = 1
    fetch_another_page = True

    full_message_list = []
    new_last_time = last_message

    # fetch all messages since last update
    while fetch_another_page:
        messages = librus_api.get_messages(page)
        for message in messages:
            if message.time > last_message:
                full_message_list.append(message)
                if message.time > new_last_time:
                    new_last_time = message.time
            else:
                fetch_another_page = False
        page += 1

    for message in full_message_list:
        for filter in channel_map:
            if filter in message.subject.lower():
                text = f"*Nowa wiadomość spełniająca filtr* {filter} *:*\n {message.subject}\n ```{message.content}```" \
                       f"\nJej autorem jest {message.teacher.first_name} {message.teacher.last_name}"
                slack_api.rtm_send_message(channel_map[filter], text)

    return new_last_time


def notice_flow(librus_api: Librus, slack_api: SlackClient, last_notice_time):

    notices = librus_api.get_notices()

    for notice in notices:
        if notice.time > last_notice_time:
            last_notice_time = notice.time

            message = f"*Nowe ogłoszenie:*\n{notice.subject}\n" \
                      f"``:`{notice.content}```\n" \
                      f"Autorem jest {notice.teacher.first_name} {notice.teacher.last_name}"

            slack_api.rtm_send_message(CHANNEL, message)
            print('messages sent')

            # archive
            archive_notice(notice)
            print('notice archived')
    return last_notice_time


if __name__ == '__main__':
    with open("last_update_times.json") as file:
        time_data = json.load(file)
        last_message = datetime.datetime.fromtimestamp(time_data["last_message"])
        last_notice = datetime.datetime.fromtimestamp(time_data["last_notice"])
        last_lucky_number = datetime.datetime.fromtimestamp(time_data["last_lucky_number"])

    sc = SlackClient(os.environ["SLACK_TOKEN"])
    lib = Librus(os.environ["LIBRUS_TOKEN"])

    if sc.rtm_connect():
        print("Slack connected")
        # bot_id = sc.api_call("api.test")["user_id"]

    while True:
        print("flow begins")

        # handle notices
        last_notice = notice_flow(lib, sc, last_notice)

        # handle lucky number
        lucky_num = lib.get_lucky_number()
        archive_lucky_number(lucky_num["number"])
        if lucky_num["date"] > last_lucky_number:
            last_lucky_number = lucky_num["date"]

            pretty_date = lucky_num["date"].strftime("%d-%m-%Y")
            message = f"*Nowy szczęśliwy numerek:* {lucky_num['number']} w dniu {pretty_date}"
            sc.rtm_send_message(CHANNEL, message)

        # handle messages
        last_message = message_flow(lib, sc, MESSAGE_CHANNEL_MAP, last_message)

        new_time_data = {}
        new_time_data["last_message"] = last_message.timestamp()
        new_time_data["last_notice"] = last_notice.timestamp()
        new_time_data["last_lucky_number"] = last_lucky_number.timestamp()
        with open("last_update_times.json", "w") as file:
            json.dump(new_time_data, file)
        print("times_updated")

        time.sleep(120)
