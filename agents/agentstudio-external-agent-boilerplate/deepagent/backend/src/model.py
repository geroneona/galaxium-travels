from langchain_core.language_models import BaseChatModel
from agentstudio_sdk.agentic_apps_api import agentic_apps_api, ModelCredentials


from langchain_aws import ChatBedrock


def init_bedrock_model(aws_credentials: ModelCredentials) -> BaseChatModel:
    """Initialize a Bedrock chat model.

    Args:
        model_id: Model ARN or model name
        aws_credentials: Dictionary containing AWS credentials with keys:
            - accessKeyId: AWS access key
            - secretAccessKey: AWS secret key
            - region: AWS region

    Returns:
        BaseChatModel instance configured for Bedrock

    Raises:
        ValueError: If required credentials are missing or provider cannot be determined
    """
    # Extract credentials from the dictionary
    model_id = aws_credentials.get("modelId")
    region = aws_credentials.get("region", "us-east-1")
    access_key_id = aws_credentials.get("accessKeyId")
    secret_access_key = aws_credentials.get("secretAccessKey")

    # Validate required credentials
    if not access_key_id or not secret_access_key:
        raise ValueError(
            "AWS credentials must contain 'accessKeyId' and 'secretAccessKey'"
        )

    # Extract provider from model ARN
    # Format: arn:aws:bedrock:region:account:inference-profile/[region.]<provider>.<model>
    # or: arn:aws:bedrock:region::foundation-model/<provider>.<model>
    model_id_lower = str(model_id).lower()
    provider = None

    if "anthropic" in model_id_lower:
        provider = "anthropic"
    elif "meta.llama" in model_id_lower:
        provider = "meta"
    elif "amazon.nova" in model_id_lower or "amazon.titan" in model_id_lower:
        provider = "amazon"
    elif "cohere.command" in model_id_lower:
        provider = "cohere"
    elif "mistral.mistral" in model_id_lower:
        provider = "mistral"
    else:
        raise ValueError(
            f"Could not determine provider from model_id: {model_id}"
        )

    return ChatBedrock(
        model_id=model_id,
        provider=provider,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region,
    )


def load_model(model_name: str):
    credentials = agentic_apps_api.get_model_credentials(model_name)
    return init_bedrock_model(credentials)
