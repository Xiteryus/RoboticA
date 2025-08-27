# -*- coding: Windows-1252 -*-
# camera.py (version modifiee pour Picamera2 avec detection de ligne - SIMPLE)
from picamera2 import Picamera2
import cv2
import time
import numpy as np
from arrow_detection import ArrowDetector

try:
    from color_detection import ColorDetector
except ImportError:
    print("Warning: color_detection module not found, color detection disabled")
    ColorDetector = None

class PiCameraStream:
    def __init__(self):
        # Initialisation SIMPLE comme dans l'ancienne version qui fonctionne
        self.picam2 = Picamera2()
        self.picam2.preview_configuration.main.size = (640, 480)
        self.picam2.preview_configuration.main.format = "BGR888"  # Retour au BGR original
        self.picam2.configure("preview")
        self.picam2.start()
        time.sleep(1)
        
        # Initialiser le detecteur de couleurs
        self.color_detector = ColorDetector() if ColorDetector else None
        self.show_color_detection = False
        self.detected_colors = []
        
        # Mode détection de ligne (NOUVELLES FONCTIONNALITÉS)
        self.line_detection_mode = False
        self.show_line_detection = False
        self.line_detection_info = {
            'angle': None,
            'direction': 'unknown',
            'line_detected': False
        }
        
        self.arrow_detector = ArrowDetector() if ArrowDetector else None
        self.arrow_detection_enabled = False
        self.arrow_direction = "none"
        self.arrow_frame = None

    def get_frame(self):
        """Retourne le frame actuel encode en JPEG"""
        try:
            frame = self.picam2.capture_array()  # Frame en BGR
            
            # Inverser manuellement les canaux Rouge et Bleu
            frame[:, :, [0, 2]] = frame[:, :, [2, 0]]  # Echange canal 0 (B) et canal 2 (R)
            
            # Appliquer la detection de couleurs si activee
            if self.show_color_detection and self.color_detector:
                try:
                    detections = self.color_detector.detect_colors(frame)
                    self.detected_colors = detections
                    frame = self.color_detector.draw_detections(frame, detections)
                    
                    # Afficher un indicateur de detection active
                    cv2.putText(frame, "DETECTION COULEUR ACTIVE", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    
                    # Afficher le nombre de couleurs detectees
                    color_count = len(detections)
                    if color_count > 0:
                        cv2.putText(frame, f"Couleurs detectees: {color_count}", 
                                   (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                except Exception as e:
                    print(f"Erreur détection couleur: {e}")
            
                        # Détection de flèche si activée
            if self.arrow_detection_enabled and self.arrow_detector:
                try:
                    self.arrow_direction, frame = self.arrow_detector.detect_arrow(frame)
                    # Afficher état
                    cv2.putText(frame, f"Fleche: {self.arrow_direction}", (10, 110),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
                except Exception as e:
                    print(f"Erreur détection flèche: {e}")
                    self.arrow_direction = "none"

            
            # Encoder en JPEG
            _, jpeg = cv2.imencode('.jpg', frame)
            return jpeg.tobytes()
            
        except Exception as e:
            print(f"Erreur capture frame: {e}")
            # En cas d'erreur, retourner une image noire simple
            error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(error_frame, "CAMERA ERROR", (200, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
            _, jpeg = cv2.imencode('.jpg', error_frame)
            return jpeg.tobytes()
            
            

    
    
    def toggle_color_detection(self):
        """Active/desactive la detection de couleurs"""
        if not self.color_detector:
            return False
        self.show_color_detection = not self.show_color_detection
        return self.show_color_detection
    
    def toggle_line_detection(self):
        """Active/désactive la détection de ligne"""
        self.show_line_detection = not self.show_line_detection
        return self.show_line_detection
    
    def get_detected_colors(self):
        """Retourne la liste des couleurs detectees"""
        return self.detected_colors if self.color_detector else []
    
    def get_dominant_color(self):
        """Retourne la couleur dominante detectee"""
        if self.detected_colors and self.color_detector:
            return self.color_detector.get_dominant_color(self.detected_colors)
        return None
    
    def get_line_detection_info(self):
        """Retourne les informations de détection de ligne"""
        return self.line_detection_info.copy()

    def stop(self):
        """Arrete la capture video"""
        try:
            self.picam2.stop()
            print("Caméra arrêtée")
        except Exception as e:
            print(f"Erreur arrêt caméra: {e}")
        
    def photo(self, filename="myphoto.png"):
        """Prend une photo et la sauvegarde"""
        try:
            frame = self.picam2.capture_array()  # Frame en BGR
            # Inverser manuellement les canaux Rouge et Bleu
            frame[:, :, [0, 2]] = frame[:, :, [2, 0]]  # Echange canal 0 (B) et canal 2 (R)
            cv2.imwrite(filename, frame)
            return filename
        except Exception as e:
            print(f"Erreur photo: {e}")
            return None
    
    def get_frame_for_processing(self):
        """
        Récupère une frame pour le traitement (détection de ligne)
        sans interférer avec le flux principal ou la détection couleur
        """
        try:
            # Capturer une frame directement depuis Picamera2
            frame = self.picam2.capture_array()
            
            # Vérifier que la frame est valide
            if frame is None:
                return None
            
            # Inverser les canaux Rouge et Bleu pour correspondre au format attendu
            frame[:, :, [0, 2]] = frame[:, :, [2, 0]]
            
            # Retourner une copie pour éviter les conflits
            return frame.copy()
            
        except Exception as e:
            print(f"Erreur get_frame_for_processing: {e}")
            return None
    #Fonction severin sur bloc note 
    def toggle_arrow_detection(self):
      """Active/désactive la détection de flèches"""
      if not self.arrow_detector:
        return False
      self.arrow_detection_enabled = not self.arrow_detection_enabled
      return self.arrow_detection_enabled
      
    def get_arrow_direction(self):
      """Retourne la dernière direction détectée par la détection de flèches"""
      return self.arrow_direction 


  