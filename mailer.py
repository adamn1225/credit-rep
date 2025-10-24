import lob, os
from dotenv import load_dotenv

load_dotenv()
lob.api_key = os.getenv("LOB_API_KEY")

BUREAU_ADDRESSES = {
    "experian": {
        "name": "Experian Dispute Department",
        "address_line1": "P.O. Box 4500",
        "address_city": "Allen",
        "address_state": "TX",
        "address_zip": "75013"
    },
    "equifax": {
        "name": "Equifax Information Services LLC",
        "address_line1": "P.O. Box 740256",
        "address_city": "Atlanta",
        "address_state": "GA",
        "address_zip": "30374-0256"
    },
    "transunion": {
        "name": "TransUnion Consumer Solutions",
        "address_line1": "P.O. Box 2000",
        "address_city": "Chester",
        "address_state": "PA",
        "address_zip": "19016"
    }
}

FROM_ADDRESS = {
    "name": "John Doe",
    "address_line1": "123 Main St",
    "address_city": "Tampa",
    "address_state": "FL",
    "address_zip": "33602"
}

def send_letter(file_path, bureau, description):
    """Mail letter through Lob and return tracking ID."""
    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        response = lob.Letter.create(
            description=description,
            to_address=BUREAU_ADDRESSES[bureau.lower()],
            from_address=FROM_ADDRESS,
            file=file_bytes,
            color=False
        )
        print(f"✅ {bureau.title()} letter sent: {response['id']}")
        return response["id"]
    except Exception as e:
        print(f"❌ Failed to send {bureau.title()} letter: {e}")
        return None
