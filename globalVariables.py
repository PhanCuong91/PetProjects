import logging,sys

msg_ticket_detail = []
log = logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("Execute.log"),
        logging.StreamHandler(sys.stdout)
    ]
)