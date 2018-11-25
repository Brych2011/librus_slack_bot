import json
import os
import time

from librus_api import Librus, get_token
from librus_api import Notice, Message

from dataclasses import dataclass
from typing import List, Dict

from slackclient import SlackClient
import datetime

# CHANNEL = "bot_testing_ground"
# ARCHIVE_PATH = "archive/"
# MESSAGE_CHANNEL_MAP = {
#     "do klasy": "bot_testing_ground",
#     "chemia": "bot_testing_ground",
#     "laboratorium": "bot_testing_ground"
# }


def archive_notice(notice: Notice, archive_path):
    fname = datetime.datetime.now().strftime("%Y-%m-%d") + "_" + notice.subject
    if os.path.exists(archive_path + fname):
        i = 2
        while os.path.exists(archive_path + fname + str(i)):
            i += 1
        fname = archive_path + fname + str(i)

    with open(fname, 'w') as file:
        file.write(notice.subject)
        file.write("\n\n")
        file.write(notice.content)
        file.write(f"\n\n Author: {notice.teacher.first_name} {notice.teacher.last_name}")


def archive_lucky_number(number, archive_path):
    with open(archive_path + "/LuckyNumbers", 'a+') as file:
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


def notice_flow(librus_api: Librus, slack_api: SlackClient, last_notice_time, channel_list, archive_path=None):

    notices = librus_api.get_notices()

    for notice in notices:
        if notice.time > last_notice_time:
            last_notice_time = notice.time

            message = f"*Nowe ogłoszenie:*\n{notice.subject}\n" \
                      f"```{notice.content}```\n" \
                      f"Autorem jest {notice.teacher.first_name} {notice.teacher.last_name}"

            for ch in channel_list:
                slack_api.rtm_send_message(ch, message)
                print('messages sent')

            # archive
            if archive_path:
                archive_notice(notice, archive_path)
            print('notice archived')
    return last_notice_time


@dataclass
class Config:
    archive_path: str
    channel_map: Dict[str, str]
    notice_channels: List[str]



if __name__ == '__main__':
    with open("last_update_times.json") as file:
        time_data = json.load(file)
        last_message = datetime.datetime.fromtimestamp(time_data["last_message"])
        last_notice = datetime.datetime.fromtimestamp(time_data["last_notice"])
        last_lucky_number = datetime.datetime.fromtimestamp(time_data["last_lucky_number"])

    with open("config.json") as file:
        config = json.load(file)
        config = Config(**config)

    with open("creds.json") as file:
        creds = json.load(file)

    librus_token = get_token(creds["login"], creds["password"])
    if librus_token:
        print("got token")

    sc = SlackClient(creds["slack_token"])
    lib = Librus(librus_token)

    if sc.rtm_connect():
        print("Slack connected")
        # bot_id = sc.api_call("api.test")["user_id"]

    while True:
        print("flow begins")

        # handle notices
        last_notice = notice_flow(lib, sc, last_notice, config.notice_channels, archive_path=config.archive_path)

        # handle lucky number
        lucky_num = lib.get_lucky_number()
        archive_lucky_number(lucky_num["number"], config.archive_path)
        if lucky_num["date"] > last_lucky_number:
            last_lucky_number = lucky_num["date"]

            pretty_date = lucky_num["date"].strftime("%d-%m-%Y")
            message = f"*Nowy szczęśliwy numerek:* {lucky_num['number']} w dniu {pretty_date}"
            for ch in config.notice_channels:
                sc.rtm_send_message(ch, message)

        # handle messages
        # last_message = message_flow(lib, sc, config.channel_map, last_message)
        # messages have to be disabled for now. I have no idea how to get a message-handling token

        new_time_data = {}
        # new_time_data["last_message"] = last_message.timestamp()
        new_time_data["last_notice"] = last_notice.timestamp()
        new_time_data["last_lucky_number"] = last_lucky_number.timestamp()
        with open("last_update_times.json", "w") as file:
            json.dump(new_time_data, file)
        print("times_updated")

        time.sleep(120)
