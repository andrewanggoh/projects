# LIBRARIES
## Environment variables
from dotenv import load_dotenv
import os

## Chatbot functionalities
import telebot
from string import Template
import emoji
from gtts import gTTS

## Data analysis
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

# SETUP: Telegram Bot API Token
load_dotenv()
TOKEN = os.environ['TOKEN']
bot = telebot.TeleBot(TOKEN)

# SETUP: Welcome Message
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    # WELCOME TEXT: chat_id, full_name, message_text
    chat_id = message.chat.id

    first_name = message.chat.first_name
    last_name = message.chat.last_name
    full_name = f'{first_name} {last_name}' if last_name is not None else first_name
    
    # Subtitute text with variable
    with open('template_text/welcome.txt', mode='r', encoding='utf-8') as f:
        content = f.read()
        temp = Template(content)
        welcome = temp.substitute(FULL_NAME = full_name)

    bot.send_message(
        chat_id,
        welcome,
        parse_mode='Markdown'
    )

# SETUP: About Chatbot Message
@bot.message_handler(commands=['about'])
def send_about(message):
    # chat_id
    chat_id = message.chat.id

    # Subtitute text with static values
    with open('template_text/about.txt', mode='r', encoding='utf-8') as f:
        content = f.read()
        temp = Template(content)
        about = temp.substitute(
            STUDENT_NAME = 'Andrew Oksner Anggoh',
            BATCH_ACADEMY = 'Vulcan Night',
            GITHUB_REPO_LINK = 'https://github.com/andrewanggoh/projects/tree/main/1.%20Telegram%20Data%20Report%20Chatbot'
        )

    bot.send_message(
        chat_id,
        about,
        parse_mode='Markdown'
    )

# DATA PREPARATION
## Read data and convert data type
df = pd.read_csv('data_input/facebook_ads_v2.csv', parse_dates=['reporting_date'])

## Get unique values of campaign_id
df['campaign_id'] = df['campaign_id'].astype('str')
unique_campaign = df['campaign_id'].unique()

## Change the data type of ad_id, age, and gender
df['ad_id'] = df['ad_id'].astype('object')
df[['age', 'gender']] = df[['age', 'gender']].astype('category') 

# SETUP: Summary Message
@bot.message_handler(commands=['summary'])
def ask_id_summary(message):
    # chat_id
    chat_id = message.chat.id

    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    for i in unique_campaign:
        markup.add(i)
    sent = bot.send_message(chat_id, 'Choose campaign to be summarized:', reply_markup=markup)

    bot.register_next_step_handler(sent, send_summary)


def send_summary(message):
    # chat_id
    chat_id = message.chat.id
    selected_campaign_id = message.text

    if selected_campaign_id in unique_campaign:
        # Filter for the selected campaign id
        df_campaign = df[df['campaign_id'] == selected_campaign_id]
        
        # Find the range date of campaign
        start_date = df_campaign['reporting_date'].min().strftime(format= '%d %b %Y')
        end_date = df_campaign['reporting_date'].max().strftime(format= '%d %b %Y')
        
        # Perform calculation
        total_spent = df_campaign['spent'].sum().astype('int64')
        total_conversion = df_campaign['total_conversion'].sum().astype('int64')
        cpc = (total_spent/total_conversion).round(1)

        # Subtitute text with variables
        with open('template_text/summary.txt', mode='r', encoding='utf-8') as f:
            content = f.read()
            temp = Template(content)
            summary = temp.substitute(
                CAMPAIGN_ID = selected_campaign_id,
                START_DATE = start_date,
                END_DATE = end_date,
                TOTAL_SPENT = f'${total_spent:,.0f}',
                TOTAL_CONVERSION = f'{total_conversion:,.0f}',
                CPC = f'${cpc:,.2f}'
            )

        bot.send_message(chat_id, summary)
    else:
        bot.send_message(chat_id, 'Campaign ID not found. Please try again!')
        ask_id_summary(message)


# SETUP: Plot message
@bot.message_handler(commands=['plot'])
def ask_id_plot(message):
    # chat_id
    chat_id = message.chat.id

    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    for i in unique_campaign:
        markup.add(i)
    sent = bot.send_message(chat_id, 'Choose campaign to be visualized:', reply_markup=markup)

    bot.register_next_step_handler(sent, send_plot)

def send_plot(message):
    # chat_id
    chat_id = message.chat.id
    selected_campaign_id = message.text

    if selected_campaign_id in unique_campaign:
        # Data preparation for plot
        df_campaign = df[df['campaign_id'] == selected_campaign_id] 
        df_plot = df_campaign.groupby('age').agg({'spent':'sum', 'approved_conversion':'sum'})
        df_plot['cpc'] = df_plot['spent']/df_plot['approved_conversion']
        
        # Data visualization
        ## Prepare 3 subplots vertically
        fig, axes = plt.subplots(3, sharex=True, dpi=300)

        ## create frameless plot
        for ax in axes:
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_visible(False)
            ax.spines['bottom'].set_visible(False)

        ## First subplot: Total Spent per Age Group
        axes[0].bar(x=df_plot.axes[0], height=df_plot['spent'], color='#AE2024')
        axes[0].set_ylabel('Total Spent', fontsize=8)

        ## Second subplot: Total Approved Conversion per Age Group
        axes[1].bar(x=df_plot.axes[0], height=df_plot['approved_conversion'], color='#000000')
        axes[1].set_ylabel('Total Approved Conversion', fontsize=8)

        ## Third subplot: Average CPC per Age Group
        axes[2].bar(x=df_plot.axes[0], height=df_plot['cpc'], color='#AE2024')
        axes[2].set_ylabel('Average CPC', fontsize=8)

        ## Set the label and title for plots
        plt.xlabel('Age Group')
        axes[0].set_title(
            f'''Average CPC, Total Spent, and Total Approved Conversion
            across Age Group for Campaign ID: {selected_campaign_id}''')

        # Create output folder
        if not os.path.exists('output'):
            os.makedirs('output')

        # Save plot
        plt.savefig('output/plot.png', bbox_inches='tight')

        # Send plot
        bot.send_chat_action(chat_id, 'upload_photo')
        with open('output/plot.png', 'rb') as img:
            bot.send_photo(chat_id, img)
            
        # Voice Message
        plot_info = list(zip(
            ['total spent', 'total approved conversion', 'average CPC'],
            df_plot.idxmax(axis = 0),
            df_plot.idxmin(axis = 0)))

        plot_text = f'This is your requested plot for Campaign ID {selected_campaign_id}.\n'
        for col, maxi, mini in plot_info:
            text = f"Age group with the highest {col} is {maxi}, while the lowest is {mini}.\n"
            plot_text += text

        # Save voice message
        speech = gTTS(text = plot_text)
        speech.save('output/plot_info.ogg')

        # Send voice message
        with open('output/plot_info.ogg', 'rb') as f:
            bot.send_voice(chat_id, f)
    else:
        bot.send_message(chat_id, 'Campaign ID not found. Please try again!')
        ask_id_plot(message)


# SETUP: Other message
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    # Emoji
    with open('template_text/default.txt', mode='r', encoding='utf-8') as f:
        temp = Template(f.read())
        default = temp.substitute(EMOJI = emoji.emojize(':folded_hands:'))
        
    bot.reply_to(message, default)

if __name__ == "__main__":
    bot.polling()
