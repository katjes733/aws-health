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
import json
import os
import logging
import datetime as dt
from datetime import timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import boto3

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
    if event and "detail" in event and event['detail']:
        send_message(event['detail'])
    else:
        health_client = boto3.client('health')
        now = dt.datetime.now()
        start_time = now - timedelta(minutes=CHECK_INTERVAL)
        all_events = health_client.describe_events(filter={'eventTypeCategories': ['issue'], \
            'lastUpdatedTimes': [{'from': start_time, 'to': now}]})['events']
        event_arns = list(map(lambda event: event['arn'],[x for x in all_events \
            if "eventScopeCode" in x and x['eventScopeCode'] == "PUBLIC"]))
        if event_arns:
            event_details = \
                health_client.describe_event_details(eventArns=event_arns)['successfulSet']
            for event_detail in event_details:
                send_message(event_detail)
        else:
            logger.info("No new events and therefore nothing to send")

def send_message(event_detail):
    """ Sends a message

    Args:
        event_detail (dictionary): the event detail
    """
    logger.info("eventDetail: %s", event_detail)
    if TEAMS_HOOK_URL or SLACK_HOOK_URL:
        if "event" in event_detail:
            event = event_detail['event']
        else:
            event = event_detail
        color = "ff0000" if event['statusCode']=="open" else "00ff00"
        event_time = event['lastUpdatedTime'].strftime('%Y-%m-%d %H:%M:%S').split(' ')
        last_event_description = list(filter(None, \
            event_detail['eventDescription']['latestDescription'].split('\n')))[-1]
        url = f"https://phd.aws.amazon.com/phd/home?region=" \
            f"{event['region']}#/dashboard/open-issues?eventID={event['arn']}&eventTab=details"
        if TEAMS_HOOK_URL:
            send_message_to_teams(event, last_event_description, color, event_time, url)
        if SLACK_HOOK_URL:
            send_message_to_slack(event, last_event_description, color, event_time, url)
    else:
        logger.info("Neither Teams nor Slack URL are set; therefore no further processing")

def send_message_to_teams(event, last_event_description, color, event_time, url):
    """ send the message to teams

    Args:
        event (dictionary): the event
        last_event_description (string): the latest event description
        c (string): the color (hex coded)
        event_time (array): array of formatted date and time
        url (string): the issue url
    """
    message = {
        "@context": "https://schema.org/extensions",
        "@type": "MessageCard",
        "themeColor": f"{color}",
        "title": f"{event['statusCode'].capitalize()} Health Notification for {event['service']}",
        "sections": [{
            "activityTitle": f"**{event['eventTypeCode']}** is in Status **{event['statusCode']}**",
            "activitySubtitle": f"{event_time[0]}, {event_time[1]} UTC",
            "facts": [
                {"name": "Service:", "value": f"{event['service']}"},
                {"name": "Region:", "value": f"{event['region']}"},
                {"name": "Event Type Code:", "value": f"{event['eventTypeCode']}"},
                {"name": "Status:", "value": f"{event['statusCode']}"},
                {"name": "Latest Description:", "value": f"{last_event_description}"}
            ]
        }],
        "summary": f"Service {event['eventTypeCode']}",
        "potentialAction" : [{
            "@type": "OpenUri", "name": "Go to Issue", "targets": [{"os": "default", "uri": url}]
        }]
    }
    send_message_to_webhook(TEAMS_HOOK_URL, message)

def send_message_to_slack(event, last_event_description, color, event_time, url):
    """ send the message to slack

    Args:
        event (dictionary): the event
        last_event_description (string): the latest event description
        c (string): the color (hex coded)
        event_time (array): array of formatted date and time
        url (string): the issue url
    """
    message = {"attachments": [{
        "color": color,
        "blocks": [{
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": \
                    f"{event['statusCode'].capitalize()} Health Notification for {event['service']}"
            }}, {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{event['eventTypeCode']}* is in Status *{event['statusCode']}*"
            }}, {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"{event_time[0]}, {event_time[1]} UTC"}]
            }, {
            "type": "divider"
            }, {
            "type": "section", "fields": [
                {"type": "mrkdwn", "text": "*Service:*"},
                {"type": "plain_text", "text": f"{event['service']}"},
                {"type": "mrkdwn", "text": "*Region:*"},
                {"type": "plain_text", "text": f"{event['region']}"},
                {"type": "mrkdwn", "text": "*Event Type Code:*"},
                {"type": "plain_text", "text": f"{event['eventTypeCode']}"},
                {"type": "mrkdwn", "text": "*Status:*"},
                {"type": "plain_text", "text": f"{event['statusCode']}"},
                {"type": "mrkdwn", "text": "*Latest Description:*"},
                {"type": "plain_text", "text": f"{last_event_description}"}
            ]}, {
            "type": "divider"
            },{
            "type": "actions",
            "elements": [{
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Go to Issue"},
                "url": url,
                "style": "primary"}
            ]}
        ]}
    ]}
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
