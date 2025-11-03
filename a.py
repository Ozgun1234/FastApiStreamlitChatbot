# test_models.py oluştur
import google.generativeai as genai

genai.configure(api_key="AIzaSyCn2dJ9QCq8ti3ehR6ewnSeVqb5J2RGMQM")

print("Available models for generateContent:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"  {m.name}")