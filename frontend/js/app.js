// Sidebar toggle
const menuToggle = document.getElementById("menu-toggle");
const sidebar = document.getElementById("sidebar");

menuToggle.addEventListener("click", () => {
  sidebar.classList.toggle("active");
});

// Auth
const loginForm = document.getElementById("login-form");
const loginSection = document.getElementById("login-section");
const appSection = document.getElementById("app-section");
const logoutBtn = document.getElementById("logout-btn");

loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;

  const { data, error } = await supabase.auth.signInWithPassword({
    email, password
  });

  if (error) {
    Swal.fire("Error", error.message, "error");
  } else {
    Swal.fire("Success", "Welcome Facilitator!", "success");
    loginSection.style.display = "none";
    appSection.style.display = "block";
    logoutBtn.style.display = "inline-block";
  }
});

logoutBtn.addEventListener("click", async () => {
  await supabase.auth.signOut();
  loginSection.style.display = "block";
  appSection.style.display = "none";
  logoutBtn.style.display = "none";
  Swal.fire("Logged out", "Goodbye!", "info");
});

// Page navigation
document.querySelectorAll(".sidebar a").forEach(link => {
  link.addEventListener("click", (e) => {
    e.preventDefault();
    const page = e.target.getAttribute("data-page");
    const pageContent = document.getElementById("page-content");

    switch(page) {
      case "dashboard":
        pageContent.innerHTML = "<h2>Dashboard</h2><p>Overview of participants.</p>";
        break;
      case "bus":
        pageContent.innerHTML = "<h2>Bus Boarding</h2><p>Scan participant QR codes here.</p>";
        break;
      case "checkin":
        pageContent.innerHTML = "<h2>Registration</h2><p>Scan participant QR codes here.</p>";
        break;
      case "meal":
        pageContent.innerHTML = "<h2>Meal Collection</h2><p>Scan participant QR codes here.</p>";
        break;
      case "reports":
        pageContent.innerHTML = "<h2>Reports</h2><p>Download attendance data here.</p>";
        break;
    }

    sidebar.classList.remove("active");
  });
});
