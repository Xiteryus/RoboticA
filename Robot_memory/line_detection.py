# -*- coding: Windows-1252 -*-
#!/usr/bin/env python3

import cv2
import numpy as np
import time

class LineDetector:
    def __init__(self):
        # Paramètres de détection de ligne
        self.threshold_value = 50  # Seuil pour détecter le noir
        self.min_area = 1500       # Aire minimale pour considérer une ligne
        self.roi_height_ratio = 0.6  # Proportion de l'image à analyser (partie basse)
        
        # Zones de l'image pour analyser la direction
        self.zone_width = 80  # Largeur de chaque zone
        
    def preprocess_frame(self, frame):
        """Prétraite l'image pour la détection de ligne"""
        if frame is None:
            return None, None
            
        # Convertir en niveaux de gris
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Définir la ROI (Region of Interest) - partie basse de l'image
        height, width = gray.shape
        roi_height = int(height * self.roi_height_ratio)
        roi = gray[height - roi_height:height, :]
        
        # Seuillage pour isoler les parties noires (ligne)
        _, thresh = cv2.threshold(roi, self.threshold_value, 255, cv2.THRESH_BINARY_INV)
        
        return roi, thresh
    
    def detect_line_contours(self, thresh_image):
        """Détecte les contours de ligne dans l'image seuillée"""
        if thresh_image is None:
            return []
            
        # Trouver les contours
        contours, _ = cv2.findContours(thresh_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filtrer les contours par aire
        valid_contours = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.min_area:
                valid_contours.append(contour)
                
        return valid_contours
    
    def analyze_line_direction(self, thresh_image):
        """Analyse la direction de la ligne et retourne l'angle de correction"""
        if thresh_image is None:
            return None, "no_image"
            
        height, width = thresh_image.shape
        
        # Diviser l'image en 3 zones: gauche, centre, droite
        zone_left = thresh_image[:, 0:self.zone_width]
        zone_center = thresh_image[:, (width//2 - self.zone_width//2):(width//2 + self.zone_width//2)]
        zone_right = thresh_image[:, (width - self.zone_width):width]
        
        # Compter les pixels blancs (ligne détectée) dans chaque zone
        pixels_left = cv2.countNonZero(zone_left)
        pixels_center = cv2.countNonZero(zone_center)
        pixels_right = cv2.countNonZero(zone_right)
        
        print(f"Pixels détectés - Gauche: {pixels_left}, Centre: {pixels_center}, Droite: {pixels_right}")
        
        # Seuils pour décider de la direction
        min_pixels = 100  # Seuil minimum pour considérer qu'il y a une ligne
        
        # Analyser la direction
        if pixels_center > min_pixels:
            if pixels_left > pixels_right + 50:
                return 110, "slight_left"  # Ligne vers la gauche
            elif pixels_right > pixels_left + 50:
                return 70, "slight_right"  # Ligne vers la droite
            else:
                return 90, "forward"  # Ligne au centre
                
        elif pixels_left > min_pixels:
            return 120, "turn_left"  # Ligne très à gauche
        elif pixels_right > min_pixels:
            return 60, "turn_right"  # Ligne très à droite
        else:
            return None, "no_line"  # Pas de ligne détectée
    
    def find_line_with_scanning(self, camera, max_attempts=8):
        """Recherche la ligne en balayant avec la caméra"""
        # Angles de scan de gauche à droite
        scan_angles = [120, 110, 100, 90, 80, 70, 60, 50]
        
        for attempt, angle in enumerate(scan_angles):
            print(f"Scan tentative {attempt + 1}/8 - Angle: {angle}°")
            
            # Orienter la caméra vers l'angle de scan
            from servo_controller_improved import servo_controller
            servo_controller.move_to_angle(1, angle, blocking=True)
            time.sleep(0.3)  # Attendre la stabilisation
            
            # Capturer et analyser l'image
            frame = camera.get_frame_for_processing()
            if frame is not None:
                _, thresh = self.preprocess_frame(frame)
                contours = self.detect_line_contours(thresh)
                
                if len(contours) > 0:
                    print(f"Ligne trouvée à l'angle {angle}°!")
                    return angle, "found"
                    
            time.sleep(0.1)
        
        print("Aucune ligne trouvée après scan complet")
        return None, "not_found"
    
    def create_debug_image(self, original_frame, thresh_image, direction_info):
        """Crée une image de debug avec les informations de détection"""
        if original_frame is None or thresh_image is None:
            return None
            
        # Redimensionner l'image seuillée pour correspondre à l'original
        height_orig = original_frame.shape[0]
        roi_height = int(height_orig * self.roi_height_ratio)
        
        # Créer une image colorée pour le debug
        debug_image = original_frame.copy()
        
        # Convertir l'image seuillée en couleur pour l'affichage
        thresh_colored = cv2.cvtColor(thresh_image, cv2.COLOR_GRAY2BGR)
        thresh_colored = cv2.resize(thresh_colored, (original_frame.shape[1], roi_height))
        
        # Superposer la zone d'analyse
        debug_image[height_orig - roi_height:height_orig, :] = thresh_colored
        
        # Ajouter les informations de direction
        angle, direction = direction_info
        if angle is not None:
            cv2.putText(debug_image, f"Direction: {direction}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(debug_image, f"Angle: {angle}°", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            cv2.putText(debug_image, "Ligne non détectée", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Dessiner les zones d'analyse
        height, width = debug_image.shape[:2]
        roi_start = height - roi_height
        
        # Zone gauche (rouge)
        cv2.rectangle(debug_image, (0, roi_start), (self.zone_width, height), (0, 0, 255), 2)
        cv2.putText(debug_image, "L", (10, roi_start + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Zone centre (vert)
        center_start = width//2 - self.zone_width//2
        center_end = width//2 + self.zone_width//2
        cv2.rectangle(debug_image, (center_start, roi_start), (center_end, height), (0, 255, 0), 2)
        cv2.putText(debug_image, "C", (center_start + 10, roi_start + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Zone droite (bleu)
        cv2.rectangle(debug_image, (width - self.zone_width, roi_start), (width, height), (255, 0, 0), 2)
        cv2.putText(debug_image, "R", (width - self.zone_width + 10, roi_start + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        
        return debug_image
    
    def detect_line_in_frame(self, frame):
        """Fonction principale pour détecter une ligne dans une image"""
        # Prétraitement
        roi, thresh = self.preprocess_frame(frame)
        
        # Détection des contours
        contours = self.detect_line_contours(thresh)
        
        # Analyse de la direction
        angle, direction = self.analyze_line_direction(thresh)
        
        # Créer l'image de debug
        debug_image = self.create_debug_image(frame, thresh, (angle, direction))
        
        return {
            'angle': angle,
            'direction': direction,
            'contours_found': len(contours),
            'line_detected': len(contours) > 0,
            'debug_image': debug_image
        }