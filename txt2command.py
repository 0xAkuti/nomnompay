import json
import pathlib
import os
import dotenv

import openai
import definitions as defs

dotenv.load_dotenv()

TRANSACTION_SCHEMA = json.loads(pathlib.Path('data/setup/BotCommand.schema.json').read_text())
SYSTEM_PROMPT = pathlib.Path('data/setup/system_prompt.txt').read_text().replace('{transactionSchema}', json.dumps(TRANSACTION_SCHEMA, indent=4))

CLIENT = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def parse_message(user_message: str) -> defs.BotCommand:
    try:
        completion = CLIENT.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            response_format=defs.BotCommand
        )
        bot_command = completion.choices[0].message
        return bot_command.parsed or defs.BotCommand(type=defs.CommandType.UNKNOWN_COMMAND, transactions=[])
    except Exception as e:
        print(f"Error parsing message: {e}")
        return defs.BotCommand(type=defs.CommandType.ERROR, transactions=[])