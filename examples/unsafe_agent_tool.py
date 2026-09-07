from agents import function_tool


@function_tool
def refund_customer(payment_client, payment_id: str):
    """Deliberately incomplete example used to prove the doctor detects gaps."""
    return payment_client.refund(payment_id)
