#!/usr/bin/env python3
# -*- coding: Windows-1252 -*-
"""
VoiceIdentify.py - Version avec base de donn�es locale de mots-cl�s
Entra�nement avec Google Speech + Reconnaissance hors ligne
"""

import subprocess
import time
import os
import json
import threading
import wave
import audioop
import statistics
import math

class DatabaseVoiceRecognizer:
    def __init__(self):
        self.output_file = "output.txt"
        self.running = False
        
        # Dossiers pour organisation
        self.audio_dir = os.path.abspath("recorded_audio")
        self.training_dir = os.path.join(self.audio_dir, "training")
        self.database_file = "voice_database.json"
        
        # Cr�er les dossiers
        for directory in [self.audio_dir, self.training_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"Dossier cr��: {directory}")
        
        # Configuration
        self.record_duration = 3
        self.commands = [
            "avancer", "reculer", "gauche", "droite", "stop",
            "photo", "centre", "regarder gauche", "regarder droite",
            "couleur", "arc-en-ciel", "start ir", "start labyrinthe"
        ]
        
        # Charger ou cr�er la base de donn�es
        self.voice_database = self.load_database()
        
        # V�rifier disponibilit� Google Speech
        self.speech_recognition_available = self.check_speech_recognition()
        
        print("??? Reconnaissance vocale avec base de donn�es locale")
        print(f"?? Audio: {self.audio_dir}")
        print(f"?? Base de donn�es: {self.database_file}")
        
    def check_speech_recognition(self):
        """V�rifie Google Speech Recognition"""
        try:
            import speech_recognition as sr
            # Test rapide de connexion
            recognizer = sr.Recognizer()
            try:
                # Test minimal pour v�rifier la connexion
                recognizer.recognize_google(sr.AudioData(b'', 16000, 2), language='fr-FR')
            except:
                pass
            print("? Google Speech Recognition disponible")
            return True
        except ImportError:
            print("? speech_recognition non install�")
            return False
        except Exception as e:
            print(f"? Google Speech peut �tre indisponible: {e}")
            return True  # On garde la possibilit� m�me si le test �choue
    
    def load_database(self):
        """Charge la base de donn�es des voix"""
        try:
            if os.path.exists(self.database_file):
                with open(self.database_file, 'r', encoding='utf-8') as f:
                    database = json.load(f)
                print(f"?? Base de donn�es charg�e: {len(database)} commandes")
                
                # Afficher les statistiques
                for command, samples in database.items():
                    print(f"  - {command}: {len(samples)} �chantillons")
                
                return database
            else:
                print("?? Nouvelle base de donn�es cr��e")
                return {}
        except Exception as e:
            print(f"? Erreur chargement base de donn�es: {e}")
            return {}
    
    def save_database(self):
        """Sauvegarde la base de donn�es"""
        try:
            with open(self.database_file, 'w', encoding='utf-8') as f:
                json.dump(self.voice_database, f, indent=2, ensure_ascii=False)
            print(f"?? Base de donn�es sauvegard�e: {self.database_file}")
            return True
        except Exception as e:
            print(f"? Erreur sauvegarde: {e}")
            return False
    
    def record_audio(self, filename_prefix="voice"):
        """Enregistre l'audio"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        audio_file = os.path.join(self.audio_dir, f"{filename_prefix}_{timestamp}.wav")
        
        try:
            print(f"?? Enregistrement ({self.record_duration}s)... PARLEZ MAINTENANT!")
            
            cmd = ['arecord', '-d', str(self.record_duration), '-f', 'cd', '-q', audio_file]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and os.path.exists(audio_file):
                file_size = os.path.getsize(audio_file)
                print(f"? Audio enregistr�: {os.path.basename(audio_file)} ({file_size} bytes)")
                
                if self.has_sound_content(audio_file):
                    return audio_file
                else:
                    print("? Audio semble �tre du silence")
                    return audio_file  # Garder quand m�me
            else:
                print("? �chec enregistrement")
                return None
                
        except Exception as e:
            print(f"? Erreur: {e}")
            return None
    
    def has_sound_content(self, audio_file):
        """V�rifie si l'audio contient du son"""
        try:
            file_size = os.path.getsize(audio_file)
            if file_size < 100000:
                return False
            
            # Analyse avec wave
            try:
                with wave.open(audio_file, 'rb') as wav_file:
                    frames = wav_file.readframes(wav_file.getnframes())
                    rms = audioop.rms(frames, wav_file.getsampwidth())
                    return rms > 100
            except:
                return file_size > 200000
                
        except:
            return True
    
    def extract_audio_features(self, audio_file):
        """Extrait les caract�ristiques audio pour la base de donn�es"""
        try:
            features = {}
            
            # Caract�ristiques de base
            file_size = os.path.getsize(audio_file)
            features['file_size'] = file_size
            
            # Analyse avec wave
            try:
                with wave.open(audio_file, 'rb') as wav_file:
                    frames = wav_file.readframes(wav_file.getnframes())
                    sample_width = wav_file.getsampwidth()
                    framerate = wav_file.getframerate()
                    
                    # Calculs audio
                    features['duration'] = len(frames) / (framerate * sample_width * wav_file.getnchannels())
                    features['rms'] = audioop.rms(frames, sample_width)
                    features['max_amplitude'] = audioop.max(frames, sample_width)
                    
                    # Analyse spectrale basique
                    # Diviser en segments pour analyser les variations
                    segment_size = len(frames) // 10
                    rms_values = []
                    
                    for i in range(0, len(frames) - segment_size, segment_size):
                        segment = frames[i:i + segment_size]
                        if len(segment) >= segment_size:
                            segment_rms = audioop.rms(segment, sample_width)
                            rms_values.append(segment_rms)
                    
                    if rms_values:
                        features['rms_variance'] = statistics.variance(rms_values) if len(rms_values) > 1 else 0
                        features['rms_mean'] = statistics.mean(rms_values)
                        features['rms_peak'] = max(rms_values)
                        
            except Exception as e:
                print(f"? Erreur analyse wave: {e}")
            
            # Analyse avec sox si disponible
            sox_features = self.get_sox_features(audio_file)
            if sox_features:
                features.update(sox_features)
            
            return features
            
        except Exception as e:
            print(f"? Erreur extraction caract�ristiques: {e}")
            return None
    
    def get_sox_features(self, audio_file):
        """Obtient des caract�ristiques suppl�mentaires avec sox"""
        try:
            result = subprocess.run([
                'sox', audio_file, '-n', 'stat'
            ], capture_output=False, stderr=subprocess.PIPE, text=True)
            
            if result.returncode == 0:
                features = {}
                
                for line in result.stderr.split('\n'):
                    if 'Length (seconds):' in line:
                        try:
                            features['sox_duration'] = float(line.split(':')[1].strip())
                        except:
                            pass
                    elif 'RMS amplitude:' in line:
                        try:
                            features['sox_rms'] = float(line.split(':')[1].strip())
                        except:
                            pass
                    elif 'Maximum amplitude:' in line:
                        try:
                            features['sox_max_amp'] = float(line.split(':')[1].strip())
                        except:
                            pass
                
                return features
                
        except FileNotFoundError:
            return {}
        except Exception:
            return {}
    
    def train_command(self, command):
        """Entra�ne une commande sp�cifique"""
        print(f"\n?? === ENTRA�NEMENT: {command.upper()} ===")
        print("Nous allons enregistrer cette commande plusieurs fois")
        print("Plus vous enregistrez, meilleure sera la reconnaissance!")
        
        if command not in self.voice_database:
            self.voice_database[command] = []
        
        samples_to_record = 5
        current_samples = len(self.voice_database[command])
        
        print(f"�chantillons actuels: {current_samples}")
        print(f"Nous allons enregistrer {samples_to_record} nouveaux �chantillons")
        
        successful_recordings = 0
        
        for i in range(samples_to_record):
            print(f"\n--- �chantillon {i + 1}/{samples_to_record} ---")
            print(f"Dites clairement: '{command}'")
            
            input("Appuyez sur Entr�e quand vous �tes pr�t...")
            
            # Enregistrer
            audio_file = self.record_audio(f"training_{command}")
            
            if audio_file:
                # V�rifier avec Google Speech si disponible
                if self.speech_recognition_available:
                    recognized = self.verify_with_google(audio_file, command)
                    if not recognized:
                        print("? Google Speech n'a pas reconnu la commande correctement")
                        retry = input("Voulez-vous garder cet �chantillon ? (y/N): ")
                        if retry.lower() != 'y':
                            os.remove(audio_file)
                            continue
                
                # Extraire les caract�ristiques
                features = self.extract_audio_features(audio_file)
                
                if features:
                    # Ajouter m�tadonn�es
                    features['timestamp'] = time.time()
                    features['audio_file'] = os.path.basename(audio_file)
                    
                    # Ajouter � la base de donn�es
                    self.voice_database[command].append(features)
                    successful_recordings += 1
                    
                    print(f"? �chantillon {successful_recordings} ajout� � la base de donn�es")
                    
                    # D�placer vers le dossier d'entra�nement
                    training_file = os.path.join(self.training_dir, os.path.basename(audio_file))
                    os.rename(audio_file, training_file)
                else:
                    print("? Impossible d'extraire les caract�ristiques")
                    if os.path.exists(audio_file):
                        os.remove(audio_file)
            else:
                print("? �chec d'enregistrement")
        
        print(f"\n?? R�sultats pour '{command}':")
        print(f"  - {successful_recordings} nouveaux �chantillons")
        print(f"  - {len(self.voice_database[command])} �chantillons total")
        
        # Sauvegarder
        self.save_database()
        
        return successful_recordings > 0
    
    def verify_with_google(self, audio_file, expected_command):
        """V�rifie l'enregistrement avec Google Speech"""
        try:
            import speech_recognition as sr
            
            recognizer = sr.Recognizer()
            
            with sr.AudioFile(audio_file) as source:
                audio = recognizer.record(source)
            
            text = recognizer.recognize_google(audio, language='fr-FR').lower()
            print(f"?? Google a entendu: '{text}'")
            
            # V�rifier si la commande attendue est dans le texte
            return expected_command.lower() in text or any(word in text for word in expected_command.split())
            
        except Exception as e:
            print(f"? V�rification Google �chou�e: {e}")
            return True  # Accepter en cas d'erreur
    
    def recognize_offline(self, audio_file):
        """Reconnaissance hors ligne avec la base de donn�es"""
        if not self.voice_database:
            print("? Base de donn�es vide - entra�nez d'abord des commandes")
            return None
        
        print("?? Reconnaissance hors ligne...")
        
        # Extraire les caract�ristiques de l'audio
        features = self.extract_audio_features(audio_file)
        
        if not features:
            print("? Impossible d'analyser l'audio")
            return None
        
        print(f"?? Caract�ristiques extraites: dur�e={features.get('duration', 0):.2f}s")
        
        # Comparer avec chaque commande dans la base de donn�es
        best_match = None
        best_score = float('inf')
        
        for command, samples in self.voice_database.items():
            if not samples:
                continue
            
            # Calculer la distance moyenne avec tous les �chantillons
            distances = []
            
            for sample in samples:
                distance = self.calculate_feature_distance(features, sample)
                if distance is not None:
                    distances.append(distance)
            
            if distances:
                avg_distance = statistics.mean(distances)
                min_distance = min(distances)
                
                # Score combin� (moyenne pond�r�e)
                score = 0.7 * avg_distance + 0.3 * min_distance
                
                print(f"  {command}: score={score:.3f} (avg={avg_distance:.3f}, min={min_distance:.3f})")
                
                if score < best_score:
                    best_score = score
                    best_match = command
        
        # Seuil de confiance
        confidence_threshold = 0.5  # Ajustable
        
        if best_match and best_score < confidence_threshold:
            confidence = max(0, 1 - best_score)
            print(f"? Reconnaissance: '{best_match}' (confiance: {confidence:.2f})")
            return best_match
        else:
            print(f"? Aucune correspondance fiable (meilleur score: {best_score:.3f})")
            return None
    
    def calculate_feature_distance(self, features1, features2):
        """Calcule la distance entre deux ensembles de caract�ristiques"""
        try:
            # Caract�ristiques � comparer avec leurs poids
            feature_weights = {
                'duration': 0.3,
                'rms': 0.2,
                'max_amplitude': 0.2,
                'rms_variance': 0.1,
                'rms_mean': 0.1,
                'file_size': 0.1
            }
            
            total_distance = 0
            total_weight = 0
            
            for feature, weight in feature_weights.items():
                if feature in features1 and feature in features2:
                    val1 = features1[feature]
                    val2 = features2[feature]
                    
                    # Normalisation et calcul de distance
                    if feature == 'duration':
                        # Distance temporelle normalis�e
                        distance = abs(val1 - val2) / max(val1, val2, 1.0)
                    elif feature in ['rms', 'max_amplitude', 'rms_mean']:
                        # Distance d'amplitude normalis�e
                        distance = abs(val1 - val2) / max(val1, val2, 1.0)
                    elif feature == 'file_size':
                        # Distance de taille normalis�e
                        distance = abs(val1 - val2) / max(val1, val2, 100000)
                    else:
                        # Distance g�n�rique
                        distance = abs(val1 - val2) / (abs(val1) + abs(val2) + 1.0)
                    
                    total_distance += distance * weight
                    total_weight += weight
            
            if total_weight > 0:
                return total_distance / total_weight
            else:
                return None
                
        except Exception as e:
            print(f"? Erreur calcul distance: {e}")
            return None
    
    def training_mode(self):
        """Mode d'entra�nement interactif"""
        print("\n?? === MODE ENTRA�NEMENT ===")
        print("Entra�nement de votre voix pour chaque commande")
        print("Plus vous enregistrez, meilleure sera la reconnaissance!")
        
        if not self.speech_recognition_available:
            print("? Google Speech non disponible - entra�nement sans v�rification")
        
        while True:
            print(f"\nCommandes disponibles:")
            for i, cmd in enumerate(self.commands, 1):
                current_samples = len(self.voice_database.get(cmd, []))
                status = "?" if current_samples >= 3 else "?" if current_samples > 0 else "?"
                print(f"  {i:2d}. {cmd} {status} ({current_samples} �chantillons)")
            
            print(f"  {len(self.commands)+1:2d}. Entra�ner toutes les commandes")
            print(f"  {len(self.commands)+2:2d}. Retour au menu principal")
            
            try:
                choice = input(f"\nChoix (1-{len(self.commands)+2}): ").strip()
                
                if choice == str(len(self.commands)+2):
                    break
                elif choice == str(len(self.commands)+1):
                    # Entra�ner toutes
                    for cmd in self.commands:
                        print(f"\n{'='*50}")
                        self.train_command(cmd)
                        print(f"{'='*50}")
                else:
                    try:
                        num = int(choice)
                        if 1 <= num <= len(self.commands):
                            command = self.commands[num - 1]
                            self.train_command(command)
                        else:
                            print("? Num�ro invalide")
                    except ValueError:
                        print("? Entr�e invalide")
                        
            except KeyboardInterrupt:
                print("\n?? Retour au menu")
                break
    
    def recognition_mode(self):
        """Mode reconnaissance avec base de donn�es"""
        print("\n?? === MODE RECONNAISSANCE HORS LIGNE ===")
        print("Utilise votre base de donn�es personnelle")
        
        if not self.voice_database:
            print("? Base de donn�es vide!")
            print("Utilisez d'abord le mode entra�nement")
            return
        
        # Statistiques
        total_samples = sum(len(samples) for samples in self.voice_database.values())
        print(f"?? Base de donn�es: {len(self.voice_database)} commandes, {total_samples} �chantillons")
        
        commands_processed = 0
        
        while self.running:
            try:
                print(f"\n[Commande #{commands_processed + 1}]")
                
                user_input = input("Appuyez sur Entr�e pour enregistrer (ou 'q' pour quitter): ").strip()
                
                if user_input.lower() == 'q':
                    break
                
                # Enregistrement
                audio_file = self.record_audio()
                
                if audio_file:
                    # Reconnaissance hors ligne
                    command = self.recognize_offline(audio_file)
                    
                    if command:
                        # �crire dans output.txt
                        if self.write_command(command):
                            commands_processed += 1
                            print(f"?? Total: {commands_processed} commandes")
                        else:
                            print("? �chec �criture")
                    else:
                        print("? Aucune commande reconnue")
                        print("?? Essayez d'entra�ner davantage cette commande")
                else:
                    print("? �chec enregistrement")
                
                time.sleep(0.5)
                
            except KeyboardInterrupt:
                print(f"\n? Arr�t - {commands_processed} commandes trait�es")
                break
    
    def write_command(self, command):
        """�crit la commande dans output.txt"""
        try:
            timestamp = time.strftime("%H:%M:%S")
            line = f"{timestamp}: {command}\n"
            
            with open(self.output_file, "a", encoding='utf-8') as f:
                f.write(line)
            
            print(f"? COMMANDE �CRITE: {command}")
            return True
            
        except Exception as e:
            print(f"? ERREUR �criture: {e}")
            return False
    
    def show_database_stats(self):
        """Affiche les statistiques de la base de donn�es"""
        print(f"\n?? === STATISTIQUES BASE DE DONN�ES ===")
        
        if not self.voice_database:
            print("Base de donn�es vide")
            return
        
        print(f"Fichier: {self.database_file}")
        print(f"Commandes: {len(self.voice_database)}")
        
        total_samples = 0
        for command, samples in self.voice_database.items():
            count = len(samples)
            total_samples += count
            status = "? Bien" if count >= 5 else "? Moyen" if count >= 3 else "? Insuffisant"
            print(f"  {command}: {count} �chantillons {status}")
        
        print(f"Total �chantillons: {total_samples}")
        
        # Taille des fichiers
        try:
            db_size = os.path.getsize(self.database_file) / 1024
            print(f"Taille base: {db_size:.1f} KB")
        except:
            pass
    
    def main_menu(self):
        """Menu principal interactif"""
        while True:
            print("\n?? === RECONNAISSANCE VOCALE AVEC BASE DE DONN�ES ===")
            print("1. ?? Mode Entra�nement (avec Internet)")
            print("2. ?? Mode Reconnaissance (hors ligne)")
            print("3. ?? Statistiques base de donn�es")
            print("4. ??? R�initialiser base de donn�es")
            print("5. ? Quitter")
            
            try:
                choice = input("\nVotre choix (1-5): ").strip()
                
                if choice == '1':
                    if self.speech_recognition_available:
                        self.training_mode()
                    else:
                        print("? Google Speech Recognition requis pour l'entra�nement")
                        print("Installez: pip3 install SpeechRecognition")
                elif choice == '2':
                    self.running = True
                    self.recognition_mode()
                    self.running = False
                elif choice == '3':
                    self.show_database_stats()
                elif choice == '4':
                    confirm = input("? �tes-vous s�r de vouloir tout supprimer? (oui/non): ")
                    if confirm.lower() == 'oui':
                        self.voice_database = {}
                        self.save_database()
                        print("? Base de donn�es r�initialis�e")
                elif choice == '5':
                    print("?? Au revoir!")
                    break
                else:
                    print("? Choix invalide")
                    
            except KeyboardInterrupt:
                print("\n?? Au revoir!")
                break

def main():
    print("=== VoiceIdentify.py - Base de Donn�es Locale ===")
    print("Entra�nement avec Google + Reconnaissance hors ligne")
    
    import sys
    
    recognizer = DatabaseVoiceRecognizer()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--train":
            recognizer.training_mode()
        elif sys.argv[1] == "--recognize":
            recognizer.running = True
            recognizer.recognition_mode()
        elif sys.argv[1] == "--stats":
            recognizer.show_database_stats()
        else:
            print("Usage:")
            print("  python3 VoiceIdentify.py           # Menu interactif")
            print("  python3 VoiceIdentify.py --train   # Mode entra�nement")
            print("  python3 VoiceIdentify.py --recognize # Mode reconnaissance")
            print("  python3 VoiceIdentify.py --stats   # Statistiques")
    else:
        recognizer.main_menu()

if __name__ == "__main__":
    main()