# -*- coding: Windows-1252 -*-
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test ultra-simple pour votre caméra
"""

import cv2
import numpy as np

def test_camera_simple():
    """Test basique de votre caméra"""
    try:
        print("=== Test ultra-simple ===")
        
        # Importer VOTRE caméra
        from camera import PiCameraStream
        print("? Import réussi")
        
        # Créer l'instance
        camera = PiCameraStream()
        print("? Caméra créée")
        
        # Tester la capture EXACTEMENT comme dans votre code
        print("Test de capture...")
        frame = camera.picam2.capture_array()
        print(f"? Frame capturée: {frame.shape}")
        
        # Appliquer VOTRE correction de canaux
        frame[:, :, [0, 2]] = frame[:, :, [2, 0]]
        print("? Canaux corrigés")
        
        # Test simple de détection de ligne
        print("Test détection basique...")
        
        # Convertir en gris
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        print(f"? Conversion gris: {gray.shape}")
        
        # Région d'intérêt (partie basse)
        height, width = gray.shape
        roi_start = height - 100
        roi = gray[roi_start:height, :]
        print(f"? ROI: {roi.shape}")
        
        # Seuillage simple
        _, binary = cv2.threshold(roi, 80, 255, cv2.THRESH_BINARY_INV)
        print(f"? Seuillage: {binary.shape}")
        
        # Compter les pixels blancs
        white_pixels = np.sum(binary == 255)
        print(f"? Pixels blancs détectés: {white_pixels}")
        
        if white_pixels > 100:
            print("? Ligne potentielle détectée !")
        else:
            print("- Pas de ligne évidente")
        
        # Fermer proprement
        camera.stop()
        print("? Caméra fermée")
        
        print("?? Test réussi !")
        return True
        
    except Exception as e:
        print(f"? Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_camera_simple()