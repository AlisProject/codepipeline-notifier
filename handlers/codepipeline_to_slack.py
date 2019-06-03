# Thanks to
# https://qiita.com/ot-nemoto/items/91886f4a18c1b4e80a45#cloudwatch
import boto3
import json
import logging
import os

from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

SLACK_CHANNEL = os.environ['SLACK_CHANNEL']

HOOK_URL = os.environ['SLACK_NOTIFICATION_URL']

CODEPIPELINE_URL = "https://{0}.console.aws.amazon.com/codepipeline/home?region={0}#/view/{1}"
GITHUB_URL = "https://github.com/{0}/{1}/tree/{2}"
CODEBUILD_URL = "https://{0}.console.aws.amazon.com/codebuild/home?region={0}#/projects/{1}/view"
ECS_URL = "https://{0}.console.aws.amazon.com/ecs/home?region={0}#/clusters/{1}/services/{2}/details"

SLACK＿MESSAGE_TEXT = '''\
*{0}* `{1}` {3} <{2}|CodePipeline>
```execution_id: {4}```
{5}
'''

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# ステータスアイコン
STATE_ICONS = {
    'STARTED': ':seedling:',
    'FAILED': ':sweat_drops:',
    'SUCCEEDED': ':rainbow::rainbow::rainbow:'
}


def lambda_handler(event, context):
    logger.debug("Event: " + str(event))

    region = event["region"]
    pipeline = event["detail"]["pipeline"]
    version = event["detail"]["version"]
    execution_id = event["detail"]["execution-id"]
    state = event["detail"]["state"]
    url = CODEPIPELINE_URL.format(region, pipeline)
    # 開始時はCodePipelineの詳細情報を追加
    detail = pipeline_details(pipeline, version, region) if state == 'STARTED' else ''

    # 通知内容
    slack_message = {
        'channel': SLACK_CHANNEL,
        'username': 'CodePipeline',
        # Please add icon to Slack by your self
        # https://slack.com/customize/emoji
        'icon_emoji': ':codepipeline:',
        'text': SLACK＿MESSAGE_TEXT.format(
            pipeline, state, url, STATE_ICONS.get(state, ''),
            execution_id, detail),
        'parse': 'none'
    }

    # 通知
    req = Request(HOOK_URL, json.dumps(slack_message).encode('utf-8'))
    try:
        response = urlopen(req)
        response.read()
        logger.info("Message posted to %s", slack_message['channel'])
    except HTTPError as e:
        logger.error("Request failed: %d %s", e.code, e.reason)
    except URLError as e:
        logger.error("Server connection failed: %s", e.reason)


# CodePipelineの詳細を取得
def pipeline_details(name, version, region):
    codepipeline = boto3.client('codepipeline').get_pipeline(
        name=name, version=int(version))
    logger.debug("get-pipeline: " + str(codepipeline))
    stages = []
    for stage in codepipeline['pipeline']['stages']:
        actions = []
        for action in stage["actions"]:
            provider = action["actionTypeId"]["provider"]
            if provider == 'GitHub':
                action_url = GITHUB_URL.format(
                    action["configuration"]["Owner"],
                    action["configuration"]["Repo"],
                    action["configuration"]["Branch"])
                actions.append(":octocat: <{0}|{1}>".format(
                    action_url, provider))
            elif provider == 'CodeBuild':
                action_url = CODEBUILD_URL.format(
                    region,
                    action["configuration"]["ProjectName"])
                actions.append(":codebuild: <{0}|{1}>".format(
                    action_url, provider))
            elif provider == 'ECS':
                action_url = ECS_URL.format(
                    region,
                    action["configuration"]["ClusterName"],
                    action["configuration"]["ServiceName"])
                actions.append(":ecs: <{0}|{1}>".format(
                    action_url, provider))
            else:
                actions.append(provider)
        stages.append("_{0}_ ( {1} )".format(stage["name"], ' | '.join(actions)))

    return ' => '.join(stages)
