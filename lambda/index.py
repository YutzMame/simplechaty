# lambda/index.py
import json
import os
import urllib.request
import re  # 正規表現モジュールをインポート
from botocore.exceptions import ClientError


# Lambda コンテキストからリージョンを抽出する関数
def extract_region_from_arn(arn):
    # ARN 形式: arn:aws:lambda:region:account-id:function:function-name
    match = re.search('arn:aws:lambda:([^:]+):', arn)
    if match:
        return match.group(1)
    return "us-east-1"  # デフォルト値

# URL
FASTAPI_URL = os.environ.get("FASTAPI_URL")

def lambda_handler(event, context):
    if not FASTAPI_URL:
        print("FASTAPI_URL environment variable is not set.")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"success": False, "error": "Configuration error: FastAPI URL is not set."})
        }
    try:
        # コンテキストから実行リージョンを取得し、クライアントを初期化
        global bedrock_client
        if bedrock_client is None:
            region = extract_region_from_arn(context.invoked_function_arn)
            bedrock_client = boto3.client('bedrock-runtime', region_name=region)
            print(f"Initialized Bedrock client in region: {region}")
        
        print("Received event:", json.dumps(event))
        
        # Cognitoで認証されたユーザー情報を取得
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")
        
        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])
        
        print("Processing message:", message)
        print(f"Calling custom LLM API at: {FASTAPI_URL}/generate")
        
       
        # ユーザーメッセージを追加
        messages.append({
            "role": "user",
            "content": message
        })
        
        # fastapi用のリクエストペイロードを構築
       
        
        # fastapi用のリクエストペイロード
        request_payload = {"prompt": message,
                            "max_new_tokens": 512,
                            "temperature": 0.7,
                            "top_p": 0.9,
                            "do_sample": True }
        
        print("Calling Bedrock invoke_model API with payload:", json.dumps(request_payload))
        
         # ペイロードをJSON文字列に変換し、バイト列にエンコード
        payload_bytes = json.dumps(request_payload).encode('utf-8')

        # FastAPI API のエンドポイントURL
        url = f"{FASTAPI_URL}/generate"

# urllib.request.Request オブジェクトを作成
        # method='POST' を明示的に指定
        req = urllib.request.Request(
            url,
            data=payload_bytes,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        # urllib.request.urlopen でAPIを呼び出し
        print("Sending request to FastAPI API...")
        with urllib.request.urlopen(req) as response:
            print(f"Received response from FastAPI API. Status code: {response.getcode()}")
            # 応答ボディを読み込み、デコード
            response_body_bytes = response.read()
            response_body_string = response_body_bytes.decode('utf-8')

        # レスポンスをJSONとして解析
        # FastAPI側のコード app (2).py は {"generated_text": "...", ...} の形式を返す想定 [cite: 1]
        response_data = json.loads(response_body_string)
        print("FastAPI API response data:", json.dumps(response_data, default=str))

        # 応答から生成されたテキストを抽出 (FastAPI側のレスポンス構造に合わせて)
        # app (2).py の generate_simple エンドポイントは "generated_text" を返す [cite: 1]
        generated_text = response_data.get("generated_text", "Error: Could not get generated text from API response.")

        # Lambdaの応答形式に変換
        # 元のコードの成功時の戻り値構造 を参考に、フロントエンドが期待する形式に合わせる
        lambda_response_body = {
            "success": True,
            "response": generated_text, }
        
        # 応答の検証
        if not response_body.get('output') or not response_body['output'].get('message') or not response_body['output']['message'].get('content'):
            raise Exception("No response content from the model")
        
       
        
        # 成功レスポンスの返却
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": messages
            })
        }
        
    except Exception as error:
        print("Error:", str(error))
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }
