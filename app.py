# importing packages

from flask import Flask, request, jsonify,render_template
from translate import Translator
from gtts import gTTS
import pygame
import os
import json
import requests
from datetime import datetime,timedelta
import speech_recognition as sr
from sqlalchemy import create_engine
from sqlalchemy import text
import pandas as pd

# flask code

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/authentication', methods=['POST'])
def authentication():
    global dest_lang
    aadhar=request.form.get('aadhar')
    dest_lang=user_database_sql_execution(aadhar)[0][0]
    text_to_speech("welcome to railway bot",dest_lang)
    menu()
    return render_template("final.html")

#trains table query execution

def train_database_sql_execution(query):
    
    df=pd.read_csv('train-details.csv')
    fingerprint=create_engine('sqlite:///:memory:',echo=True)
    df.to_sql(name='trains',con=fingerprint)
    with fingerprint.connect() as conn:
        result=conn.execute(text(query))
    return result.all()

#users table query execution

def user_database_sql_execution(aadhar):
    df=pd.read_csv('users.csv')
    fingerprint=create_engine('sqlite:///:memory:',echo=True)
    df.to_sql(name='users',con=fingerprint)
    with fingerprint.connect() as conn:
        result=conn.execute(text("select language from users where aadhar="+aadhar))
    return result.all()

#recognizing speech from user

def recognize_speech(text,target_language):
    text_to_speech(text,target_language)
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source,timeout=4)
        text_to_speech("please wait while we are procressing your request",dest_lang)
        user_input = recognizer.recognize_google(audio, language='en')
        return user_input
    except sr.UnknownValueError:
        text_to_speech("sorry i couldn't understand",target_language)
        return ""
    except sr.RequestError:
        text_to_speech("sorry there was an issue",target_language)
        return ""
    except sr.WaitTimeoutError:
        user_input=recognize_speech_same("listening timedout, can you say it again",dest_lang)
        return user_input

#conversion of text to speech 

def text_to_speech(text, target_language):
    translator = Translator(to_lang=target_language)
    text=translator.translate(text)
    tts = gTTS(text=text, lang=target_language, slow=False)
    audio_file = "voices/language.mp3"
    tts.save(audio_file)
    pygame.mixer.init()
    pygame.mixer.music.load(audio_file)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        continue
    pygame.mixer.music.stop()
    pygame.mixer.quit()
    os.remove(audio_file)

#text to text translation

def translate_text(text,target_language):
    translator = Translator(from_lang=target_language,to_lang='en')
    text=translator.translate(text)
    return text

#reverse translation of text

def translate_text_reverse(text,target_language):
    translator = Translator(from_lang='en',to_lang=target_language)
    text=translator.translate(text)
    return text

#recognize speech of same language

def recognize_speech_same(text,target_language):
    text_to_speech(text,target_language)
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source,timeout=4)
        text_to_speech("please wait while we are procressing your request",dest_lang)
        user_input = recognizer.recognize_google(audio, language=dest_lang)
        return user_input
    except sr.UnknownValueError:
        text_to_speech("sorry i couldn't understand",target_language)
        return ""
    except sr.RequestError:
        text_to_speech("sorry there was an issue",target_language)
        return ""
    except sr.WaitTimeoutError:
        user_input=recognize_speech_same("listening timedout, can you say it again",dest_lang)
        return user_input

#stops sql execution

def stop_sql_execution(query):
    df=pd.read_csv('stops.csv',encoding='iso-8859-1')
    df.head()
    fingerprint=create_engine('sqlite:///:memory:',echo=True,pool_size=20)
    df.to_sql(name='destinations',con=fingerprint)
    with fingerprint.connect() as conn:
        result=conn.execute(text(query))
    return result.all()


#menu of the railway bot

def menu():
    user_input=recognize_speech_same("if you want to get train details say 'one' , if you want to get available trains say 'two', if you want to get platform number of your train say 'three'",dest_lang)
    
    while(user_input==""):
        user_input=recognize_speech_same("can you say it again",dest_lang)
    
    text_to_speech("your response has been recieved",dest_lang)
    if translate_text(user_input,dest_lang)=='1' or translate_text(user_input,dest_lang).lower()=='one':
        train_name=recognize_speech("can you tell me your train name",dest_lang).lower()
        
        while train_name=="":
                train_name=recognize_speech_same("can you say it again",dest_lang)

        text_to_speech("your response has been recieved",dest_lang)        
        result=train_database_sql_execution("select trainname,arrival,destination,platform,startingtime,reachingtime,id from trains where trainname=\""+train_name+"\";")
        if not result:
            text_to_speech("sorry, there are no trains with the name "+train_name,dest_lang)
        else:
            for i in result:
                tn=str(i[6]).replace('',' ')
                text="train number: "+tn+",train name: "+i[0]+",destination: "+i[2]+",starting time: "+str(i[4])+",reaching time: "+str(i[5])+",platform number: "+str(i[3])
                text_to_speech(text,dest_lang)

    elif translate_text(user_input,dest_lang)=='2' or translate_text(user_input,dest_lang).lower()=='two':
        user_input=recognize_speech("can you tell me where do you want to go",dest_lang)
        
        while user_input=="":
            user_input=recognize_speech("can you say it again",dest_lang)
        user_input=user_input.lower()
        text_to_speech("your response has been recieved",dest_lang)
        if user_input!="":
            current_time = datetime.now().strftime('%H:%M')
            span_time = (datetime.now() + timedelta(hours=3)).strftime('%H:%M')
            result=stop_sql_execution("select trainname,stations from destinations where stations like '%"+user_input+"%';")
            after_time=""
            within_time=""
            for i in result:
                stop_strings=i[1].split(";")
                train_schedule = {}
                for stop_string in stop_strings:
                    stop_info = stop_string.strip().split(":",1)
                    station_name = stop_info[0].strip().replace(":", "").replace(" ", "")
                    train_schedule[station_name] = stop_info[1].strip().split(',')
                if(train_schedule["visakhapatnam"][1]<=span_time and train_schedule["visakhapatnam"][1]>current_time):
                    within_time=within_time+"\n train name:"+i[0]+ ",destination: "+user_input+",starting time:"+train_schedule["visakhapatnam"][1]+",reaching time:"+train_schedule[user_input][0]
                else:
                    after_time=after_time+"\n train name:"+i[0]+ ",starting time:"+train_schedule["visakhapatnam"][1]+",reaching time:"+train_schedule[user_input][0]

            if(within_time==""):
                word=recognize_speech_same("sorry, there are no trains in 3 hours, do you want the trains after 3 hours? tell 'yes' if you want the trains or tell 'no'",dest_lang)
                print(translate_text(word,dest_lang))
                while word=="":
                    word=recognize_speech_same("can you say it again",dest_lang)
                if(translate_text(word,dest_lang).lower()=="yes"):
                    text_to_speech(after_time,dest_lang)

            elif(within_time=="" and after_time==""):
                text_to_speech("sorry, the requested station data is not available",dest_lang)
                
            else:
                text_to_speech(within_time,dest_lang)

            # if(after_time=="" and within_time==""):
            #     text_to_speech("sorry there are no trains",dest_lang)
            # result=train_database_sql_execution("select trainname,arrival,destination,platform,startingtime,reachingtime,id from trains where destination=\""+user_input.lower()+"\" and time(\""+current_time+"\")<=startingtime and time(\""+span_time+"\")>=startingtime;")
            # if not result:
            #     word=recognize_speech_same("sorry, there are no trains in 3 hours, do you want the trains after 3 hours? tell 'yes' if you want the trains or tell 'no'",dest_lang)
            #     print(translate_text(word,dest_lang))
            #     while word=="":
            #         word=recognize_speech_same("can you say it again",dest_lang)
            #     if(translate_text(word,dest_lang).lower()=="yes"):
            #         result=train_database_sql_execution("select trainname,arrival,destination,platform,startingtime,reachingtime,id from trains where destination=\""+user_input.lower()+"\" order by startingtime asc;")
            #         for i in result:
            #             tn=str(i[6]).replace('',' ')
            #             text="train number: "+tn+",train name: "+i[0]+",destination: "+i[2]+",starting time: "+str(i[4])+",reaching time: "+str(i[5])+",platform number: "+str(i[3])
            #             text_to_speech(text,dest_lang)
            # else:
            #     for i in result:
            #         tn=str(i[6]).replace('',' ')
            #         text="train number: "+tn+",train name: "+i[0]+",destination: "+i[2]+",starting time: "+str(i[4])+",reaching time: "+str(i[5])+",platform number: "+str(i[3])
            #         text_to_speech(text,dest_lang)

    elif translate_text(user_input,dest_lang)=='3' or translate_text(user_input,dest_lang).lower()=='three':
        train_name=recognize_speech("can you tell me your train name",dest_lang).lower()
        
        while train_name=="":
            train_name=recognize_speech("can you say it again",dest_lang) 
        print(train_name)
        text_to_speech("your response has been recieved",dest_lang)           
        result=stop_sql_execution("select trainname,platform from destinations where trainname=\""+train_name+"\";")
        if not result:
            text_to_speech("sorry, there are no trains with the name "+train_name,dest_lang)
        else:
            for i in result:
                text="train name: "+i[0]+",platform number: "+str(i[1])
                text_to_speech(text,dest_lang)

    else:
        text_to_speech("tell the correct number",dest_lang)
    
    extra_question=recognize_speech_same("Do you have any questions?. If you have any questions tell 'yes', If you don't have questions tell 'no'",dest_lang)
    while extra_question=="":
        extra_question=recognize_speech_same("can you say it again",dest_lang)
    if(translate_text(extra_question,dest_lang).lower()=="yes"):
        menu()
    else:
        text_to_speech("thank you", dest_lang)


if __name__ == '__main__':
    app.run(debug=True)