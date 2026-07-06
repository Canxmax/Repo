import os
import threading
import time
from tkinter import messagebox
import customtkinter as cctk
from googletrans import Translator
from gtts import gTTS
import numpy as np
import pygame
import scipy.io.wavfile as wav
import sounddevice as sd
import speech_recognition as sr

# --- Tema ve Renk Ayarları ---
cctk.set_appearance_mode("Dark")
cctk.set_default_color_theme("blue")

# Dil Sözlüğü
DIL_ISIMLERI = {
    "Türkçe": "tr",
    "İngilizce": "en",
    "İspanyolca": "es",
    "Rusça": "ru",
    "Portekizce": "pt",
    "Endonezya Dili": "id",
    "Polonca": "pl",
    "İtalyanca": "it",
}


class ModernCeviriUygulamasi:

    def __init__(self, pencere):
        self.pencere = pencere
        self.pencere.title("AI Sesli Çevirmen v2.5")
        self.pencere.geometry("550x650")
        self.pencere.resizable(False, False)

        # --- Başlık ---
        self.baslik = cctk.CTkLabel(
            pencere,
            text="🎙️ AI Sesli Anlık Çevirmen",
            font=cctk.CTkFont(family="Arial", size=22, weight="bold"),
        )
        self.baslik.pack(pady=20)

        # --- Ayarlar Paneli (Kart Görünümü) ---
        self.kart = cctk.CTkFrame(pencere, corner_radius=15)
        self.kart.pack(pady=10, padx=30, fill="x")

        # Süre Ayarı
        cctk.CTkLabel(
            self.kart, text="Kayıt Süresi (Saniye):", font=("Arial", 12)
        ).grid(row=0, column=0, padx=15, pady=15, sticky="w")
        self.sure_kutusu = cctk.CTkComboBox(
            self.kart, values=["3", "5", "10", "15", "20"], width=90
        )
        self.sure_kutusu.set("5")
        self.sure_kutusu.grid(row=0, column=1, padx=15, pady=15, sticky="e")

        # Konuşma Dili
        cctk.CTkLabel(self.kart, text="Konuşma Dili:", font=("Arial", 12)).grid(
            row=1, column=0, padx=15, pady=10, sticky="w"
        )
        self.kombo_konusma = cctk.CTkComboBox(
            self.kart, values=list(DIL_ISIMLERI.keys()), width=160
        )
        self.kombo_konusma.set("Türkçe")
        self.kombo_konusma.grid(row=1, column=1, padx=15, pady=10, sticky="e")

        # Çeviri Dili
        cctk.CTkLabel(self.kart, text="Çeviri Dili:", font=("Arial", 12)).grid(
            row=2, column=0, padx=15, pady=10, sticky="w"
        )
        self.kombo_ceviri = cctk.CTkComboBox(
            self.kart, values=list(DIL_ISIMLERI.keys()), width=160
        )
        self.kombo_ceviri.set("İngilizce")
        self.kombo_ceviri.grid(row=2, column=1, padx=15, pady=10, sticky="e")

        # --- Durum Etiketi ---
        self.durum_etiketi = cctk.CTkLabel(
            pencere,
            text="Sisteme bağlanmaya hazır",
            font=cctk.CTkFont(family="Arial", size=13, slant="italic"),
            text_color="#5A92E5",
        )
        self.durum_etiketi.pack(pady=10)

        # --- Ana Aksiyon Butonu ---
        self.buton_basla = cctk.CTkButton(
            pencere,
            text="🎤 Dinlemeyi Başlat",
            font=cctk.CTkFont(family="Arial", size=14, weight="bold"),
            height=45,
            corner_radius=10,
            fg_color="#24a0ed",
            hover_color="#1183ca",
            command=self.islemi_baslat_thread,
        )
        self.buton_basla.pack(pady=10, padx=30, fill="x")

        # --- Çıktı Alanları ---
        cctk.CTkLabel(
            pencere, text="Söylenen Metin", font=("Arial", 11, "bold")
        ).pack(anchor="w", padx=35, pady=(10, 2))
        self.metin_soylenen = cctk.CTkTextbox(
            pencere, height=70, corner_radius=8
        )
        self.metin_soylenen.pack(pady=5, padx=30, fill="x")

        cctk.CTkLabel(
            pencere, text="Çevrilen Metin", font=("Arial", 11, "bold")
        ).pack(anchor="w", padx=35, pady=(10, 2))
        self.metin_cevrilen = cctk.CTkTextbox(
            pencere, height=70, corner_radius=8
        )
        self.metin_cevrilen.pack(pady=5, padx=30, fill="x")

    def islemi_baslat_thread(self):
        # Programın kilitlenmesini önlemek için arka planda çalıştırıyoruz
        threading.Thread(target=self.islem_akisi, daemon=True).start()

    def islem_akisi(self):
        ses_dosyasi = "output.wav"
        gecici_ses = "gui_output.mp3"

        try:
            # Arayüzü kilitle ve temizle
            self.buton_basla.configure(state="disabled", fg_color="#555555")
            self.metin_soylenen.delete("1.0", cctk.END)
            self.metin_cevrilen.delete("1.0", cctk.END)

            sure = int(self.sure_kutusu.get())
            kod_konusma = DIL_ISIMLERI[self.kombo_konusma.get()]
            kod_ceviri = DIL_ISIMLERI[self.kombo_ceviri.get()]

            # 1. Ses Kaydı
            self.durum_etiketi.configure(
                text=f"Mikrofon aktif, konuşun... ({sure} sn)",
                text_color="#ff4d4d",
            )
            sample_rate = 44100
            recording = sd.rec(
                int(sure * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype="int16",
            )
            sd.wait()

            self.durum_etiketi.configure(
                text="Ses dalgaları çözümleniyor...", text_color="#ffcc00"
            )
            wav.write(ses_dosyasi, sample_rate, recording)

            # 2. Konuşma Tanıma
            recognizer = sr.Recognizer()
            with sr.AudioFile(ses_dosyasi) as source:
                audio = recognizer.record(source)

            try:
                text = recognizer.recognize_google(audio, language=kod_konusma)
                self.metin_soylenen.insert(cctk.END, text)
            except Exception:
                self.durum_etiketi.configure(
                    text="Ses algılanamadı, tekrar deneyin.",
                    text_color="#ff4d4d",
                )
                return

            # 3. Çeviri
            self.durum_etiketi.configure(
                text=" Yapay zeka çevirisi yapılıyor...", text_color="#ffcc00"
            )
            translator = Translator()
            translated = translator.translate(text, dest=kod_ceviri)
            self.metin_cevrilen.insert(cctk.END, translated.text)

            # 4. Seslendirme (Text-to-Speech)
            self.durum_etiketi.configure(
                text=" Çeviri seslendiriliyor...", text_color="#2db300"
            )
            tts = gTTS(text=translated.text, lang=kod_ceviri, slow=False)
            tts.save(gecici_ses)

            # Pygame ses çalma motorunu güvenli başlatma ve sıfırlama
            pygame.mixer.init()
            pygame.mixer.music.load(gecici_ses)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                time.sleep(0.1)

            # Dosya kilidini tamamen kaldırmak için motoru kapatıyoruz
            pygame.mixer.music.unload()
            pygame.mixer.quit()

            self.durum_etiketi.configure(
                text=" Çeviri başarıyla tamamlandı!", text_color="#2db300"
            )

        except Exception as e:
            messagebox.showerror(
                "Hata", f"İşlem sırasında bir hata oluştu:\n{e}"
            )
            self.durum_etiketi.configure(
                text=" Hata nedeniyle durduruldu.", text_color="#ff4d4d"
            )
        finally:
            # Temizlik ve Butonu Aktif Etme
            self.buton_basla.configure(state="normal", fg_color="#24a0ed")

            # Dosyaları arka planda silerek sistemi temiz tut
            try:
                if os.path.exists(gecici_ses):
                    os.remove(gecici_ses)
                if os.path.exists(ses_dosyasi):
                    os.remove(ses_dosyasi)
            except Exception:
                pass  # Dosya o an silinemezse programın çökmesini engelle


# --- Uygulamayı Başlat ---
if __name__ == "__main__":
    root = cctk.CTk()
    uygulama = ModernCeviriUygulamasi(root)
    root.mainloop()
