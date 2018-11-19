import os

import requests
import datetime

from librus_api.data_containers import Teacher, Notice, Message


def prepare_header(token):
    return {"Authorization": f"Bearer {token}"}


def api_url(*args):
    base = "https://api.librus.pl/2.0"
    for field in args:
        base += "/" + field
    return base


def remove_escapes(s: str):
    return s.encode('utf-8').decode('unicode-escape')


class Librus:

    def __init__(self, token):
        self.token = token

        self.default_header = prepare_header(token)

        self.teacher_data = {}
        self.category_data = {}

        # fetch basic data
        try:
            data = self.raw_call("Me")
            root = data["Me"]

            print("Authorization complete for user {} {}.".format(root["User"]["FirstName"], root["User"]["LastName"]))
            self.user = root["User"]

        except Exception as e:
            print("Error in initialization. This API instance should not be trusted")
            raise e

    def raw_call(self, *args):
        url = api_url(*args)
        try:
            data = requests.get(url, headers=self.default_header).json()
            if data.get("Status") == "Error":
                raise Exception("wrong API call")
            return data
        except Exception as e:
            print("Error retrieving data: \n {}".format(repr(e)))

    def get_lucky_number(self):
        data = self.raw_call("LuckyNumbers")
        root = data["LuckyNumber"]
        result = {}
        result["number"] = root["LuckyNumber"]
        result["date"] = datetime.datetime.strptime(root["LuckyNumberDay"], "%Y-%m-%d")
        return result

    def get_notices(self):
        data = self.raw_call("SchoolNotices")
        root = data["SchoolNotices"]
        result = []
        for entry in root:
            new_entry = Notice(
                start=datetime.datetime.strptime(entry["StartDate"], "%Y-%m-%d"),
                end=datetime.datetime.strptime(entry["EndDate"], "%Y-%m-%d"),
                subject=entry["Subject"],
                content=entry["Content"],
                teacher=self.get_teacher_info(entry["AddedBy"]["Id"]),
                time=datetime.datetime.strptime(entry["CreationDate"], "%Y-%m-%d %H:%M:%S")
            )
            result.append(new_entry)

        return result

    def get_teacher_info(self, teacher_id, from_message=False):

        # possible issue with mixing teacher id between messages and notices
        # TODO get rid of the issue
        result = self.teacher_data.get(teacher_id)
        if result is not None:
            return result
        else:
            if from_message:
                data = self.raw_call("Messages", "User", str(teacher_id))
            else:
                data = self.raw_call("Users", str(teacher_id))
            root = data["User"]

            result = Teacher(
                first_name=root["FirstName"],
                last_name=root["LastName"][0] + root["LastName"][1:].lower(),
                id=root["Id"]
            )

            self.teacher_data[teacher_id] = result
            return result

    def get_messages(self, page):
        data = self.raw_call("Messages", f"?page={page}")

        message_root =data["Messages"]
        result = []

        for entry in message_root:
            new_entry = Message(
                id=entry["Id"],
                url=entry["Url"],
                teacher=self.get_teacher_info(entry["Sender"]["Id"], from_message=True),
                subject=remove_escapes(entry["Subject"]),
                content=remove_escapes(entry["Body"]),
                has_attachments=entry["AddedFiles"],
                time=datetime.datetime.fromtimestamp(entry["SendDate"]))
            result.append(new_entry)

        return result





if __name__ == '__main__':
    token = os.environ['LIBRUS_TOKEN']

    api = Librus(token)
    print(api.get_lucky_number())

    ogloszenia = api.get_notices()
    # messages = api.get_messages(1)

    possible_stuff = api.raw_call("Root")["Resources"]
    l = [i for i in possible_stuff]
    l.sort()
    for i in l:
        print(i)
