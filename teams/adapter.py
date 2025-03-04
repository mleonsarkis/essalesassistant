from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings
from config.settings import MICROSOFT_APP_ID, MICROSOFT_APP_PASSWORD

adapter_settings = BotFrameworkAdapterSettings(
    app_id=MICROSOFT_APP_ID,
    app_password=MICROSOFT_APP_PASSWORD
)
adapter = BotFrameworkAdapter(adapter_settings)
