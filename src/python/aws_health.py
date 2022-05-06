"""
MIT License

Copyright (c) 2022 Martin Macecek

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Lambda function for aws health
"""
import json, os, logging, boto3
import datetime as dt
from datetime import timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Microsoft Teams url webhook
TEAMS_HOOK_URL = os.environ['TeamsHookUrl']
# Slack url webhook
SLACK_HOOK_URL = os.environ['SlackHookUrl']
CHECK_INTERVAL = int(os.environ['CheckTime'])

levels = {
    'critical': logging.CRITICAL,
    'error': logging.ERROR,
    'warn': logging.WARNING,
    'info': logging.INFO,
    'debug': logging.DEBUG
}
logger = logging.getLogger()
try:
    logger.setLevel(levels.get(os.getenv('LOG_LEVEL', 'info').lower()))
except KeyError as e:
    logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """ Entry function for invocation in Lambda

    Args:
        event (dictionary): the event for this lambda function
        context (dictionary): the context for this lambda function
    """
    logger.info("event: %s", event)
    logger.debug("context: %s", context)
    if event and "detail" in event:
        send_message(event['detail'])
    else:
        hClient = boto3.client('health')
        toDt = dt.datetime.now()
        fromDt = toDt - timedelta(minutes=CHECK_INTERVAL)
        allEvents = hClient.describe_events(filter={'eventTypeCategories': ['issue'], 'lastUpdatedTimes': [{'from': fromDt, 'to': toDt}]})['events']
        eventArns = list(map(lambda event: event['arn'],[x for x in allEvents if "eventScopeCode" in x and x['eventScopeCode'] == "PUBLIC"]))
        if eventArns:
            eDs = hClient.describe_event_details(eventArns=eventArns)['successfulSet']
            for eD in eDs:
                send_message(eD)
        else:
            logger.info("No new events and therefore nothing to send")

def send_message(eD):
    """ Sends a message

    Args:
        eD (dictionary): the event detail
    """
    logger.info("eventDetail: %s", eD)
    if "event" in eD:
        ev = eD['event']
    else:
        ev = eD
    c = "ff0000" if ev['statusCode']=="open" else "00ff00"
    dt_f = ev['lastUpdatedTime'].strftime('%Y-%m-%d %H:%M:%S').split(' ')
    lED = list(filter(None, eD['eventDescription']['latestDescription'].split('\n')))[-1]
    iUrl = f"https://phd.aws.amazon.com/phd/home?region={ev['region']}#/dashboard/open-issues?eventID={ev['arn']}&eventTab=details"
    if TEAMS_HOOK_URL:
        send_message_to_teams(ev, lED, c, dt_f, iUrl)
    if SLACK_HOOK_URL:
        send_message_to_slack(ev, lED, c, dt_f, iUrl)

def send_message_to_teams(ev, lED, c, dt_f, iUrl):
    """ send the message to teams

    Args:
        ev (dictionary): the event
        lED (string): the latest event description
        c (string): the color (hex coded)
        dt_f (array): array of formatted date and time
        iUrl (string): the issue url
    """
    message = {
        "@context": "https://schema.org/extensions",
        "@type": "MessageCard",
        "themeColor": f"{c}",
        "title": f"{ev['statusCode'].capitalize()} Health Notification for {ev['service']}",
        "sections": [{
            "activityTitle": f"**{ev['eventTypeCode']}** is in Status **{ev['statusCode']}**",
            "activitySubtitle": f"{dt_f[0]}, {dt_f[1]} UTC",
            "facts": [
                {"name": "Service:", "value": f"{ev['service']}"},
                {"name": "Region:", "value": f"{ev['region']}"},
                {"name": "Event Type Code:", "value": f"{ev['eventTypeCode']}"},
                {"name": "Status:", "value": f"{ev['statusCode']}"},
                {"name": "Latest Description:", "value": f"{lED}"}
            ]
        }],
        "summary": f"Service {ev['eventTypeCode']}",
        "potentialAction" : [{
            "@type": "OpenUri", "name": "Go to Issue", "targets": [{"os": "default", "uri": iUrl}]
        }]
    }
    send_message_to_webhook(TEAMS_HOOK_URL, message)

def send_message_to_slack(ev, lED, c, dt_f, iUrl):
    """ send the message to slack

    Args:
        ev (dictionary): the event
        lED (string): the latest event description
        c (string): the color (hex coded)
        dt_f (array): array of formatted date and time
        iUrl (string): the issue url
    """
    message = {
        "attachments": [
            {
                "color": c,
                "blocks": [
                    {"type": "header", "text": {"type": "plain_text", "text": f"{ev['statusCode'].capitalize()} Health Notification for {ev['service']}"}},
                    {"type": "section", "text": {"type": "mrkdwn", "text": f"*{ev['eventTypeCode']}* is in Status *{ev['statusCode']}*"}},
                    {"type": "context", "elements": [{"type": "mrkdwn", "text": f"{dt_f[0]}, {dt_f[1]} UTC"}]},
                    {"type": "divider"},
                    {"type": "section", "fields": [
                            {"type": "mrkdwn", "text": "*Service:*"}, {"type": "plain_text", "text": f"{ev['service']}"},
                            {"type": "mrkdwn", "text": "*Region:*"}, {"type": "plain_text", "text": f"{ev['region']}"},
                            {"type": "mrkdwn", "text": "*Event Type Code:*"}, {"type": "plain_text", "text": f"{ev['eventTypeCode']}"},
                            {"type": "mrkdwn", "text": "*Status:*"}, {"type": "plain_text", "text": f"{ev['statusCode']}"},
                            {"type": "mrkdwn", "text": "*Latest Description:*"}, {"type": "plain_text", "text": f"{lED}"}
                        ]
                    },
                    {"type": "divider"},
                    {"type": "actions", "elements": [
                            {"type": "button", "text": {"type": "plain_text", "text": "Go to Issue"}, "url": iUrl, "style": "primary"}
                        ]
                    }
                ]
            }
        ]
    }
    send_message_to_webhook(SLACK_HOOK_URL, message)

def send_message_to_webhook(url, message):
    """ send the message to the designated webhook url

    Args:
        url (string): the destination url
        message (dictionary): the message
    """
    request = Request(
        url,
        json.dumps(message).encode('utf-8'))
    try:
        response = urlopen(request)
        response.read()
        logger.info("Message posted")
    except HTTPError as err:
        logger.error("Request failed: %s %s", err.code, err.reason)
    except URLError as err:
        logger.error("Server connection failed: %s", err.reason)
