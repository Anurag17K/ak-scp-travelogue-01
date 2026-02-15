// theme.js

// API URL
const THEME_API_BASE = "https://z1s4ahgav3.execute-api.us-east-1.amazonaws.com/prod/themes/";

// Store original styles
const originalBodyBg = document.body.style.backgroundColor || "";
const originalBodyColor = document.body.style.color || "";
const originalCardStyles = [];
document.querySelectorAll(".card").forEach(card => {
    originalCardStyles.push({ bg: card.style.backgroundColor || "", color: card.style.color || "" });
});

// Apply theme
function applyTheme(theme) {
    document.body.style.backgroundColor = theme.background;
    document.body.style.color = theme.text;
    document.querySelectorAll(".card").forEach(card => {
        card.style.backgroundColor = theme.background;
        card.style.color = theme.text;
    });
}

// Reset to default theme
function resetTheme() {
    document.body.style.backgroundColor = originalBodyBg;
    document.body.style.color = originalBodyColor;
    document.querySelectorAll(".card").forEach((card, i) => {
        card.style.backgroundColor = originalCardStyles[i].bg;
        card.style.color = originalCardStyles[i].color;
    });
}

// Event listeners
document.addEventListener("DOMContentLoaded", () => {
    const changeBtn = document.getElementById("changeThemeBtn");
    const panel = document.getElementById("themePanel");
    const randomMainBtn = document.getElementById("randomMainBtn");
    const randomPanel = document.getElementById("randomCategoryPanel");

    // Toggle theme panel
    changeBtn.addEventListener("click", () => {
        panel.style.display = panel.style.display === "block" ? "none" : "block";
    });

    // Default / Dark radio buttons
    document.querySelectorAll('input[name="themeOption"]').forEach(radio => {
        radio.addEventListener("change", function() {
            if (this.value === "default") resetTheme();
            if (this.value === "dark") {
                fetch(THEME_API_BASE + "dark")
                    .then(r => r.json())
                    .then(data => applyTheme(data))
                    .catch(e => console.error("Theme API error:", e));
            }
        });
    });

    // Toggle random categories
    randomMainBtn.addEventListener("click", () => {
        randomPanel.style.display = randomPanel.style.display === "block" ? "none" : "block";
    });

    // Random category buttons
    randomPanel.querySelectorAll("button").forEach(btn => {
        btn.addEventListener("click", () => {
            const category = btn.dataset.category;
            fetch(THEME_API_BASE + category)
                .then(r => r.json())
                .then(data => applyTheme(data))
                .catch(e => console.error("Theme API error:", e));
        });
    });

    // Close panel if clicked outside
    document.addEventListener("click", function(e) {
        if (!panel.contains(e.target) && e.target !== changeBtn) {
            panel.style.display = "none";
            randomPanel.style.display = "none";
        }
    });
});
