import discord
import os
from discord.ext import commands
import json
from datetime import datetime
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

# Bot configuration
intents = discord.Intents.all()
intents.message_content = True
intents.members = True
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Data storage
DATA_FILE = 'f1_predictions.json'
DRIVERS_FILE = 'drivers.json'

# Initialize data structures
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)
else:
    data = {
        'active_prediction': None,
        'predictions': {},
        'leaderboard': {}
    }

if os.path.exists(DRIVERS_FILE):
    with open(DRIVERS_FILE, 'r') as f:
        drivers_data = json.load(f)
else:
    drivers_data = {'drivers': {}}
    with open(DRIVERS_FILE, 'w') as f:
        json.dump(drivers_data, f, indent=4)

def save_drivers():
    with open(DRIVERS_FILE, 'w') as f:
        json.dump(drivers_data, f, indent=4)

# Helper function to save data
def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Calculate points based on prediction accuracy
def calculate_points(prediction, actual_result):
    points = 0
    for i, driver in enumerate(prediction):
        if driver in actual_result:
            actual_position = actual_result.index(driver)
            position_difference = abs(i - actual_position)

            if position_difference == 0:
                points += 10
            elif position_difference == 1:
                points += 7
            elif position_difference == 2:
                points += 5
            elif position_difference == 3:
                points += 3
            elif position_difference == 4:
                points += 1
    return points

@bot.event
async def on_ready():
    print(f'Bot is ready! Logged in as {bot.user}')
    try:
        await bot.wait_until_ready()
        synced = await bot.tree.sync()
        print(f"Successfully synced {len(synced)} command(s)")
        print("Help command should now be working!")
    except Exception as e:
        print(f"Error syncing commands: {e}")

@bot.tree.command(name="help", description="Shows how to use the F1 Prediction Bot")
async def help(interaction: discord.Interaction):
    help_message = """
🏎️ **F1 Prediction Bot Commands** 🏎️

**For Everyone:**
`/predict` - Submit your top 5 prediction
`/my_prediction` - View your current prediction
`/status` - Check active prediction and who has submitted
`/leaderboard` - View the overall points leaderboard
`/race_history` - List all completed races
`/race_history_details` - View details for a specific race

**Admin Commands:**
`/start_prediction` - Start a new prediction round
`/end_prediction` - End prediction and submit actual results

**Tips:**
- Use consistent driver names (e.g., "Verstappen" not "Max" or "Max Verstappen")
- You can update your prediction by submitting a new one before the prediction ends
"""
    await interaction.response.send_message(help_message)

@bot.tree.command(name="start_prediction", description="Start a new prediction for a race (admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def start_prediction(interaction: discord.Interaction, race_name: str):
    if data['active_prediction']:
        await interaction.response.send_message(f"❌ There's already an active prediction for {data['active_prediction']}. End it first with `/end_prediction`.")
        return

    data['active_prediction'] = race_name
    data['predictions'][race_name] = {
        'started_at': datetime.now().isoformat(),
        'predictions': {},
        'actual_result': None,
        'is_active': True
    }
    save_data()

    await interaction.response.send_message(f"🏁 Prediction for **{race_name}** has started! Use `/predict` to submit your top 5 prediction.")

@bot.tree.command(name="predict", description="Submit your prediction for the top 5 drivers")
async def predict(interaction: discord.Interaction, pos1: int, pos2: int, pos3: int, pos4: int, pos5: int):
    if not data['active_prediction']:
        await interaction.response.send_message("❌ There's no active prediction right now. Ask an admin to start one.")
        return

    race_name = data['active_prediction']
    user_id = str(interaction.user.id)

    # Check if user has already predicted
    if user_id in data['predictions'][race_name]['predictions']:
        await interaction.response.send_message("❌ You have already submitted a prediction for this race. Use `/my_prediction` to view your current prediction.")
        return

    # Validate all drivers exist
    predictions = [str(pos) for pos in [pos1, pos2, pos3, pos4, pos5]]
    invalid_drivers = [pos for pos in predictions if pos not in drivers_data['drivers']]
    if invalid_drivers:
        await interaction.response.send_message(f"❌ Invalid driver numbers: {', '.join(invalid_drivers)}")
        return

    # Convert numbers to names
    driver1 = drivers_data['drivers'][str(pos1)]
    driver2 = drivers_data['drivers'][str(pos2)]
    driver3 = drivers_data['drivers'][str(pos3)]
    driver4 = drivers_data['drivers'][str(pos4)]
    driver5 = drivers_data['drivers'][str(pos5)]
    if not data['active_prediction']:
        await interaction.response.send_message("❌ There's no active prediction right now. Ask an admin to start one.")
        return

    race_name = data['active_prediction']
    prediction = [driver1, driver2, driver3, driver4, driver5]

    data['predictions'][race_name]['predictions'][str(interaction.user.id)] = {
        'user': interaction.user.name,
        'prediction': prediction,
        'submitted_at': datetime.now().isoformat()
    }
    save_data()

    await interaction.response.send_message(f"✅ {interaction.user.mention}, your prediction for **{race_name}** has been recorded:\n1. {driver1}\n2. {driver2}\n3. {driver3}\n4. {driver4}\n5. {driver5}")

@bot.tree.command(name="end_prediction", description="End the prediction and submit actual results (admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def end_prediction(interaction: discord.Interaction, pos1: int, pos2: int, pos3: int, pos4: int, pos5: int):
    # Validate all drivers exist
    positions = [str(pos) for pos in [pos1, pos2, pos3, pos4, pos5]]
    invalid_drivers = [pos for pos in positions if pos not in drivers_data['drivers']]
    if invalid_drivers:
        await interaction.response.send_message(f"❌ Invalid driver numbers: {', '.join(invalid_drivers)}")
        return

    # Convert numbers to names
    driver1 = drivers_data['drivers'][str(pos1)]
    driver2 = drivers_data['drivers'][str(pos2)]
    driver3 = drivers_data['drivers'][str(pos3)]
    driver4 = drivers_data['drivers'][str(pos4)]
    driver5 = drivers_data['drivers'][str(pos5)]
    if not data['active_prediction']:
        await interaction.response.send_message("❌ There's no active prediction to end.")
        return

    race_name = data['active_prediction']
    actual_result = [driver1, driver2, driver3, driver4, driver5]

    data['predictions'][race_name]['actual_result'] = actual_result
    data['predictions'][race_name]['is_active'] = False
    data['predictions'][race_name]['ended_at'] = datetime.now().isoformat()

    results_message = f"🏁 **Results for {race_name}**\nActual Top 5:\n1. {driver1}\n2. {driver2}\n3. {driver3}\n4. {driver4}\n5. {driver5}\n\n**Points:**\n"

    for user_id, prediction_data in data['predictions'][race_name]['predictions'].items():
        user_name = prediction_data['user']
        prediction = prediction_data['prediction']
        points = calculate_points(prediction, actual_result)

        if user_id not in data['leaderboard']:
            data['leaderboard'][user_id] = {
                'user': user_name,
                'total_points': 0,
                'predictions_made': 0
            }

        data['leaderboard'][user_id]['total_points'] += points
        data['leaderboard'][user_id]['predictions_made'] += 1

        predicted_drivers = "\n".join([f"{i+1}. {driver}" for i, driver in enumerate(prediction)])
        results_message += f"**{user_name}**: {points} points\nPredicted:\n{predicted_drivers}\n\n"

    data['active_prediction'] = None
    save_data()

    await interaction.response.send_message(results_message)

@bot.tree.command(name="leaderboard", description="Show the current leaderboard")
async def show_leaderboard(interaction: discord.Interaction):
    if not data['leaderboard']:
        await interaction.response.send_message("❌ No predictions have been made yet. The leaderboard is empty.")
        return

    sorted_leaderboard = sorted(
        data['leaderboard'].values(),
        key=lambda x: x['total_points'],
        reverse=True
    )

    leaderboard_message = "🏆 **F1 Prediction Leaderboard**\n\n"
    for i, entry in enumerate(sorted_leaderboard):
        leaderboard_message += f"{i+1}. **{entry['user']}**: {entry['total_points']} points ({entry['predictions_made']} predictions)\n"

    await interaction.response.send_message(leaderboard_message)

@bot.tree.command(name="status", description="Check if there's an active prediction and who has predicted")
async def prediction_status(interaction: discord.Interaction):
    if not data['active_prediction']:
        await interaction.response.send_message("❌ There's no active prediction right now.")
        return

    race_name = data['active_prediction']
    if race_name not in data['predictions']:
        data['predictions'][race_name] = {
            'started_at': datetime.now().isoformat(),
            'predictions': {},
            'actual_result': None,
            'is_active': True
        }
    predictions = data['predictions'][race_name]['predictions']

    status_message = f"🏁 **Active Prediction: {race_name}**\n\nSubmitted predictions:\n"
    if not predictions:
        status_message += "None yet."
    else:
        for prediction_data in predictions.values():
            user_name = prediction_data['user']
            status_message += f"- {user_name}\n"

    await interaction.response.send_message(status_message)

@bot.tree.command(name="my_prediction", description="Check your current prediction")
async def my_prediction(interaction: discord.Interaction):
    if not data['active_prediction']:
        await interaction.response.send_message("❌ There's no active prediction right now.")
        return

    race_name = data['active_prediction']
    user_id = str(interaction.user.id)

    if user_id not in data['predictions'][race_name]['predictions']:
        await interaction.response.send_message(f"❌ You haven't submitted a prediction for {race_name} yet.")
        return

    prediction = data['predictions'][race_name]['predictions'][user_id]['prediction']
    prediction_message = f"🏁 Your prediction for **{race_name}**:\n"
    for i, driver in enumerate(prediction):
        prediction_message += f"{i+1}. {driver}\n"

    await interaction.response.send_message(prediction_message)

@bot.tree.command(name="race_history", description="View list of completed races")
async def race_history(interaction: discord.Interaction):
    completed_races = [r for r in data['predictions'] if not data['predictions'][r]['is_active'] and data['predictions'][r]['actual_result']]

    if not completed_races:
        await interaction.response.send_message("❌ No completed races found.")
        return

    races_list = "\n".join([f"- {race}" for race in completed_races])
    await interaction.response.send_message(f"**Completed Races:**\n{races_list}\n\nUse `/race_history_details race_name` to view details for a specific race.")

@bot.tree.command(name="race_history_details", description="View details for a specific completed race")
async def race_history_details(interaction: discord.Interaction, race_name: str):
    if race_name not in data['predictions'] or data['predictions'][race_name]['is_active']:
        await interaction.response.send_message(f"❌ No completed race found with name '{race_name}'.")
        return

    race_data = data['predictions'][race_name]
    actual_result = race_data['actual_result']

    history_message = f"🏁 **Results for {race_name}**\nActual Top 5:\n"
    for i, driver in enumerate(actual_result):
        history_message += f"{i+1}. {driver}\n"

    history_message += "\n**User Predictions and Points:**\n"
    for prediction_data in race_data['predictions'].values():
        user_name = prediction_data['user']
        prediction = prediction_data['prediction']
        points = calculate_points(prediction, actual_result)
        predicted_drivers = ", ".join(prediction)
        history_message += f"**{user_name}**: {points} points - Predicted: {predicted_drivers}\n"

    await interaction.response.send_message(history_message)

@bot.tree.command(name="add_driver", description="Add a driver to the roster (admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def add_driver(interaction: discord.Interaction, number: int, name: str):
    drivers_data['drivers'][str(number)] = name
    save_drivers()
    await interaction.response.send_message(f"✅ Added driver #{number}: {name}")

@bot.tree.command(name="remove_driver", description="Remove a driver from the roster (admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def remove_driver(interaction: discord.Interaction, number: int):
    if str(number) in drivers_data['drivers']:
        del drivers_data['drivers'][str(number)]
        save_drivers()
        await interaction.response.send_message(f"✅ Removed driver #{number}")
    else:
        await interaction.response.send_message("❌ Driver not found")

@bot.tree.command(name="clear_prediction", description="Force clear the active prediction (admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def clear_prediction(interaction: discord.Interaction):
    if not data['active_prediction']:
        await interaction.response.send_message("❌ There's no active prediction to clear.")
        return
    
    race_name = data['active_prediction']
    data['active_prediction'] = None
    if race_name in data['predictions']:
        data['predictions'].pop(race_name)
    save_data()
    await interaction.response.send_message(f"✅ Cleared active prediction for {race_name}")

@bot.tree.command(name="list_drivers", description="List all available drivers")
async def list_drivers(interaction: discord.Interaction):
    if not drivers_data['drivers']:
        await interaction.response.send_message("No drivers have been added yet.")
        return

    drivers_list = "\n".join([f"#{num}: {name}" for num, name in sorted(drivers_data['drivers'].items(), key=lambda x: int(x[0]))])
    await interaction.response.send_message(f"**Available Drivers:**\n{drivers_list}")



# Run the bot
discord_api_token = os.getenv("DiscordAPIToken")
if not discord_api_token:
    raise ValueError("DiscordAPIToken environment variable not set. Please set it before running the bot.")

bot.run(discord_api_token)