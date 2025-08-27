# -*- coding: Windows-1252 -*-
import cv2
import numpy as np

class ColorDetector:
    def __init__(self):
        # Definition des plages HSV pour seulement 3 couleurs (rouge, vert, bleu)
        self.color_ranges = {
            'rouge': {
                'lower1': np.array([0, 70, 70]),      # Plus strict sur saturation/valeur
                'upper1': np.array([10, 255, 255]),
                'lower2': np.array([170, 70, 70]),
                'upper2': np.array([180, 255, 255])
            },
            'vert': {
                'lower': np.array([45, 70, 70]),      # Plage plus etroite
                'upper': np.array([75, 255, 255])
            },
            'bleu': {
                'lower': np.array([105, 70, 70]),     # Plus strict
                'upper': np.array([125, 255, 255])
            }
        }
        
        self.detected_colors = []
        self.detection_active = False
        self.min_area = 1500  # Seuil d'aire plus eleve
        self.max_detections = 3  # Limite le nombre de detections par couleur
    
    def detect_colors(self, frame):
        """Detecte les couleurs dans une image"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        detected = []
        
        # Appliquer un leger flou pour reduire le bruit
        hsv = cv2.GaussianBlur(hsv, (5, 5), 0)
        
        for color_name, ranges in self.color_ranges.items():
            if 'lower1' in ranges:  # Pour le rouge qui a deux plages
                mask1 = cv2.inRange(hsv, ranges['lower1'], ranges['upper1'])
                mask2 = cv2.inRange(hsv, ranges['lower2'], ranges['upper2'])
                mask = cv2.bitwise_or(mask1, mask2)
            else:
                mask = cv2.inRange(hsv, ranges['lower'], ranges['upper'])
            
            # Filtrage plus agressif du bruit
            kernel = np.ones((7,7), np.uint8)  # Kernel plus grand
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            
            # Erosion supplementaire pour eliminer les petites zones
            mask = cv2.erode(mask, kernel, iterations=1)
            mask = cv2.dilate(mask, kernel, iterations=1)
            
            # Trouver les contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Trier les contours par aire (plus grand en premier)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)
            
            color_count = 0
            for contour in contours:
                if color_count >= self.max_detections:  # Limite par couleur
                    break
                    
                area = cv2.contourArea(contour)
                if area > self.min_area:  # Seuil plus eleve
                    # Verifier que la forme n'est pas trop allongee ou bizarre
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = float(w) / h
                    if 0.3 <= aspect_ratio <= 3.0:  # Rapport largeur/hauteur raisonnable
                        
                        # Verifier que la detection couvre une partie significative du rectangle
                        rect_area = w * h
                        if area / rect_area > 0.3:  # Au moins 30% du rectangle
                            center_x = x + w // 2
                            center_y = y + h // 2
                            
                            detected.append({
                                'color': color_name,
                                'center': (center_x, center_y),
                                'area': area,
                                'bbox': (x, y, w, h)
                            })
                            color_count += 1
        
        # Trier par aire pour privilegier les plus grandes detections
        detected = sorted(detected, key=lambda x: x['area'], reverse=True)
        
        # Limiter le nombre total de detections affichees
        return detected[:5]  # Maximum 5 detections au total
    
    def draw_detections(self, frame, detections):
        """Dessine les detections sur l'image"""
        for detection in detections:
            color = detection['color']
            center = detection['center']
            bbox = detection['bbox']
            area = detection['area']
            
            # Couleurs BGR pour l'affichage (seulement rouge, vert, bleu)
            colors_bgr = {
                'rouge': (0, 0, 255),
                'vert': (0, 255, 0),
                'bleu': (255, 0, 0)
            }
            
            color_bgr = colors_bgr.get(color, (255, 255, 255))
            
            # Dessiner le rectangle avec contour plus epais
            x, y, w, h = bbox
            cv2.rectangle(frame, (x, y), (x + w, y + h), color_bgr, 3)
            
            # Dessiner le point central plus gros
            cv2.circle(frame, center, 8, color_bgr, -1)
            cv2.circle(frame, center, 8, (255, 255, 255), 2)  # Contour blanc
            
            # Afficher le nom de la couleur avec fond
            text = f"{color.upper()}"
            font_scale = 0.8
            thickness = 2
            
            # Calculer la taille du texte pour le fond
            (text_width, text_height), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
            
            # Dessiner le fond du texte
            cv2.rectangle(frame, (x, y - text_height - 15), (x + text_width + 10, y - 5), color_bgr, -1)
            
            # Dessiner le texte en blanc
            cv2.putText(frame, text, (x + 5, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 
                       font_scale, (255, 255, 255), thickness)
            
            # Afficher l'aire plus discretement
            area_text = f"{int(area)}"
            cv2.putText(frame, area_text, (x, y + h + 20), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.4, color_bgr, 1)
        
        return frame
    
    def get_dominant_color(self, detections):
        """Retourne la couleur avec la plus grande aire detectee"""
        if not detections:
            return None
        
        return max(detections, key=lambda x: x['area'])['color']
    
    def set_sensitivity(self, level):
        """Ajuste la sensibilite de detection (1=strict, 2=normal, 3=souple)"""
        if level == 1:  # Strict
            self.min_area = 2000
            self.max_detections = 2
        elif level == 2:  # Normal (par defaut)
            self.min_area = 1500
            self.max_detections = 3
        elif level == 3:  # Souple
            self.min_area = 1000
            self.max_detections = 4
        else:
            self.min_area = 1500
            self.max_detections = 3
    
    def toggle_detection(self):
        """Active/desactive la detection"""
        self.detection_active = not self.detection_active
        return self.detection_active