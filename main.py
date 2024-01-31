import logging
import aiogram
from aiogram import types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import openai
import os
from dotenv import load_dotenv

load_dotenv()
# Configure logging
logging.basicConfig(level=logging.INFO)

# Your bot token
API_TOKEN = os.getenv('BOT_TOKEN')

# OpenAI API key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY

# Initialize the bot
bot = aiogram.Bot(token=API_TOKEN)
dp = aiogram.Dispatcher(bot)

# Global variables to store user choices
selected_location = None
selected_checklist_item = None
user_comment = None
user_photo = None

# Add a state to store information about the current user state
user_state = None


# Function to send a question to OpenAI
async def send_question_to_openai(question):
    try:
        # Receiving a report from OpenAI
        openai_response = openai.completions.create(
            model="gpt-3.5-turbo",
            prompt=question,
            temperature=0.7,
            max_tokens=100,
        )
        # Sending a report to the user
        return ("Report from OpenAI:" + openai_response.choices[0].text)
    except openai.RateLimitError as e:
        return ("Error: You have exceeded your current OpenAI quota.")
    except Exception as e:
        return (f"Error: {str(e)}")


# Command /start
@dp.message_handler(commands=['start'])
async def on_start(message: types.Message):
    # Greet the user
    await message.answer("Welcome! This is a checklist bot. Choose a location:")

    # Create a keyboard for location selection
    locations_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    locations = ["Location 1", "Location 2", "Location 3", "Location 4", "Location 5"]
    for location in locations:
        locations_keyboard.add(KeyboardButton(location))

    await message.answer("Choose a location:", reply_markup=locations_keyboard)


# Handling location selection
@dp.message_handler(lambda message: message.text in ["Location 1", "Location 2", "Location 3", "Location 4", "Location 5"])
async def process_location(message: types.Message):
    global selected_location, user_state
    selected_location = message.text

    # Display checklist items for the selected location
    await message.answer(f"You chose {selected_location}. Now, select a checklist item:")

    # Create a keyboard for checklist item selection
    checklist_items = ["Item 1", "Item 2", "Item 3", "Item 4", "Item 5"]
    for item in checklist_items:
        await message.answer(item)

    # Create a keyboard for selecting the state of the checklist item
    state_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    state_keyboard.add(KeyboardButton("All Clear"))
    state_keyboard.add(KeyboardButton("Leave a Comment"))

    await message.answer("Select the state:", reply_markup=state_keyboard)

    # Change the user state to "waiting_for_state"
    user_state = "waiting_for_state"


# Handling the selection of the checklist item state
@dp.message_handler(lambda message: message.text in ["All Clear", "Leave a Comment"])
async def process_state(message: types.Message):
    global user_comment, user_state
    if message.text == "Leave a Comment":
        await message.answer("Enter your comment:")
        # Change the user state to "waiting_for_comment"
        user_state = "waiting_for_comment"
        return

    user_comment = None
    await process_user_input(message)


# Handling user text input
@dp.message_handler(lambda message: True)
async def process_user_input(message: types.Message):
    global user_comment, user_state
    user_input = message.text

    if user_state == "waiting_for_comment":
        user_comment = user_input
        await message.answer("Your comment has been recorded. Thank you!")
        user_state = "waiting_for_photo"  # Change the state to "waiting_for_photo"
        # Prompt the user to upload a photo
        await message.answer("Upload a photo:")
        return

    elif user_state == "waiting_for_state":
        await message.answer(f"Selected {selected_checklist_item} in {selected_location}. Selected state: {user_input}.")

        # Send a question to OpenAI
        question = f"Checklist: {selected_checklist_item} - {selected_location} - {message.from_user.username}"
        openai_response = await send_question_to_openai(question)

        # Send OpenAI response to the user
        await message.answer("OpenAI Report:" + openai_response)

        # Prompt the user to upload a photo only if they left a comment
        if user_comment:
            await message.answer("Upload a photo:")
            user_state = "waiting_for_photo"


# Handling user photo upload
@dp.message_handler(content_types=types.ContentType.PHOTO)
async def process_photo(message: types.Message):
    global user_photo, user_state
    # Get the photo from the message
    user_photo = message.photo[-1]

    # Save the photo on the server
    file_id = user_photo.file_id
    file_path = await bot.get_file(file_id)
    file_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file_path.file_path}"

    await message.answer(f"The photo was successfully uploaded. Thank you! Photo URL:\n{file_url}")

    # Send a question to OpenAI
    question = f"Checklist: {selected_checklist_item} - {selected_location} - {message.from_user.username}\nUser left a comment: {user_comment}\nUser uploaded a photo: {file_url}"

    try:
        # Get the OpenAI response
        openai_response = await send_question_to_openai(question)

        # Send OpenAI response to the user
        await message.answer("OpenAI Report:" + openai_response)

    except openai.error.OpenAIError as e:
        await message.answer(f"Error: {str(e)}")

# Start the bot
if __name__ == '__main__':
    from aiogram import executor

    executor.start_polling(dp, skip_updates=True)
