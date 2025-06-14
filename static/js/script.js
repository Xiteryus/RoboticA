const keyMap = {
    "z": "haut",
    "s": "bas",
    "q": "gauche",
    "d": "droite",
    "r": "stop"
  };

  let currentDirection = null;
  let startTimeout = null;

  document.addEventListener("keydown", function(event) {
    const key = event.key;
    const dir = keyMap[key];
    if (!dir) return;

    // Contrôle moteur z/s avec temporisation
    if (dir === "haut" || dir === "bas") {
      if (currentDirection === dir) return;

      startTimeout = setTimeout(() => {
        currentDirection = dir;
        sendDirection("start", dir);
      }, 200);
    }

    // Virages instantanés q/d ou reset r
    if (dir === "gauche" || dir === "droite" || dir === "stop") {
      sendMoove(dir); // Appelle /moove avec direction
    }
  });

  document.addEventListener("keyup", function(event) {
    const key = event.key;
    const dir = keyMap[key];
    if (!dir) return;

    if (dir === "haut" || dir === "bas") {
      clearTimeout(startTimeout);
      if (currentDirection) {
        sendDirection("stop");
        currentDirection = null;
      }
    }
  });

  function sendDirection(action, direction = "") {
    const formData = new FormData();
    if (direction) formData.append("direction", direction);
    fetch(`/moteur/${action}`, {
      method: "POST",
      body: formData
    });
  }

  function sendMoove(direction) {
    const formData = new FormData();
    formData.append("direction", direction);
    fetch("/moove", {
      method: "POST",
      body: formData
    });
  }