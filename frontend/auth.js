
// =============================================
// CHRONEXA AI - CUSTOM TOAST NOTIFICATION SYSTEM
// =============================================

function showToast(message, type = "success") {

    const oldToast = document.querySelector(".toast-notification");

    if (oldToast) {
        oldToast.remove();
    }

    const toast = document.createElement("div");
    toast.className = `toast-notification ${type}`;

    const icon = document.createElement("span");
    icon.className = "toast-icon";
    icon.textContent = type === "success" ? "✓" : "✕";

    const text = document.createElement("span");
    text.className = "toast-message";
    text.textContent = message;

    toast.appendChild(icon);
    toast.appendChild(text);

    document.body.appendChild(toast);

    console.log("Chronexa toast:", message);

    setTimeout(() => {

        toast.classList.add("toast-hide");

        setTimeout(() => {
            toast.remove();
        }, 400);

    }, 3000);
}


// =============================================
// SHOW TOAST AFTER PAGE REDIRECTION
// =============================================

document.addEventListener("DOMContentLoaded", function () {

    console.log("Chronexa auth.js loaded successfully.");

    const message = sessionStorage.getItem("chronexaToast");

    if (message) {
        showToast(message);
        sessionStorage.removeItem("chronexaToast");
    }

});


// =============================================
// CHRONEXA AI - AUTHENTICATION
// =============================================

const API_URL = "http://127.0.0.1:8000";


// =====================================
// CHRONEXA BROWSER NOTIFICATIONS
// =====================================

async function requestNotificationPermission() {

    if (!("Notification" in window)) {
        showToast("Browser notifications are not supported.", "error");
        return;
    }

    if (Notification.permission === "default") {
        const permission = await Notification.requestPermission();

        if (permission === "granted") {
            showToast("Browser notifications enabled!");
        } else {
            showToast("Browser notification permission was not granted.", "error");
        }

    } else if (Notification.permission === "granted") {
        showToast("Browser notifications are already enabled!");

    } else {
        showToast("Please enable notifications in your browser settings.", "error");
    }
}
// =============================================
// USER REGISTRATION
// =============================================

const registerForm = document.getElementById("registerForm");

if (registerForm) {

    registerForm.addEventListener("submit", async function (event) {

        event.preventDefault();

        const username = document.getElementById("name").value.trim();
        const email = document.getElementById("email").value.trim();
        const password = document.getElementById("password").value;
        const confirmPassword = document.getElementById("confirmPassword").value;

        // Check password confirmation
        if (password !== confirmPassword) {

            showToast("Passwords do not match!", "error");

            return;
        }

        try {

            const response = await fetch(`${API_URL}/auth/register`, {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    username: username,
                    email: email,
                    password: password
                })

            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "Registration failed");
            }

            // Save success message before redirecting
            sessionStorage.setItem(
                "chronexaToast",
                "You have successfully registered!"
            );

            window.location.href = "login.html";

        } catch (error) {

            console.error("Registration error:", error);

            showToast(error.message, "error");

        }

    });

}


// =============================================
// USER LOGIN
// =============================================

const loginForm = document.getElementById("loginForm");

if (loginForm) {

    loginForm.addEventListener("submit", async function (event) {

        event.preventDefault();

        const email = document.getElementById("email").value.trim();
        const password = document.getElementById("password").value;

        try {

            const response = await fetch(`${API_URL}/auth/login`, {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    email: email,
                    password: password
                })

            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "Login failed");
            }

            // Save authentication token
            sessionStorage.setItem("access_token", data.access_token);

            // Save success message before redirecting
            sessionStorage.setItem(
                "chronexaToast",
                "You have successfully logged in!"
            );

            window.location.href = "index.html";

        } catch (error) {

            console.error("Login error:", error);

            showToast(error.message, "error");

        }

    });

}


// =============================================
// DASHBOARD DATA
// =============================================

const dashboard =
    window.location.pathname.endsWith("index.html") ||
    window.location.pathname.endsWith("/");

if (dashboard) {

    const token = sessionStorage.getItem("access_token");

    if (!token) {

        window.location.href = "login.html";

    } else {

        // =====================================
        // FETCH DASHBOARD DATA
        // =====================================

        async function fetchDashboardData(endpoint) {

            const response = await fetch(`${API_URL}${endpoint}`, {

                method: "GET",

                headers: {
                    "Authorization": `Bearer ${token}`
                }

            });

            const data = await response.json();

            if (!response.ok) {

                throw new Error(
                    data.detail || `Unable to load ${endpoint}`
                );

            }

            if (Array.isArray(data)) {
                return data;
            }

            if (data && Array.isArray(data.items)) {
                return data.items;
            }
            if (data && Array.isArray(data.tasks)) {
                return data.tasks;
            }

            if (data && Array.isArray(data.notes)) {
                return data.notes;
            }

            if (data && Array.isArray(data.schedules)) return data.schedules;

            return [];
        }


        // =============================================
// CHRONEXA AI - COMPLETE TASK MANAGEMENT
// =============================================

let editingTaskId = null;


// =============================================
// TASK POPUP ELEMENTS
// =============================================

const taskModal = document.getElementById("taskModal");
const taskForm = document.getElementById("taskForm");

const taskTitleInput = document.getElementById("taskTitle");
const taskDescriptionInput = document.getElementById("taskDescription");

const closeTaskButton = document.getElementById("closeTaskModal");
const cancelTaskButton = document.getElementById("cancelTaskBtn");

const saveTaskButton = taskForm.querySelector(
    'button[type="submit"]'
);


// =============================================
// OPEN TASK POPUP
// =============================================

const openTaskButtons = document.querySelectorAll(
    ".primary-btn, .tasks-card .small-create-btn"
);

openTaskButtons.forEach(button => {

    button.addEventListener("click", function () {

        editingTaskId = null;

        taskForm.reset();

        taskModal.querySelector("h2").textContent = "Create a New Task ✦";

        saveTaskButton.textContent = "+ Create Task";

        taskModal.style.display = "flex";

    });

});


// =============================================
// CLOSE TASK POPUP
// =============================================

function closeTaskModal() {

    taskModal.style.display = "none";

    taskForm.reset();

    editingTaskId = null;

}

closeTaskButton.addEventListener("click", closeTaskModal);

cancelTaskButton.addEventListener("click", closeTaskModal);

taskModal.addEventListener("click", function (event) {

    if (event.target === taskModal) {
        closeTaskModal();
    }

});


// =============================================
// LOAD AND DISPLAY TASKS
// =============================================

async function loadTasks() {

    const taskList = document.querySelector(".task-list");

    try {

        const response = await fetch(`${API_URL}/tasks`, {

            headers: {
                "Authorization": `Bearer ${token}`
            }

        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Unable to load tasks.");
        }

        const tasks = Array.isArray(data)
            ? data
            : (data.tasks || data.items || []);

        const taskCount = document.querySelector(".stat-purple h2");

        if (taskCount) {
            taskCount.textContent = String(tasks.length).padStart(2, "0");
        }

        if (!taskList) return;

        taskList.innerHTML = "";

        if (tasks.length === 0) {

            taskList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">✓</div>
                    <h4>No tasks yet</h4>
                    <p>Create your first task and get started.</p>
                </div>
            `;

            return;
        }

        tasks.forEach(task => {

            const item = document.createElement("div");

            item.style.padding = "16px";
            item.style.marginBottom = "12px";
            item.style.borderRadius = "14px";
            item.style.background = task.completed
                ? "#f0fff7"
                : "#f8f5ff";

            item.style.border = "1px solid #eee7f8";

            // Task title
            const title = document.createElement("h4");

            title.textContent = task.title;

            title.style.marginBottom = "8px";

            if (task.completed) {
                title.style.textDecoration = "line-through";
                title.style.color = "#929292";
            }

            // Task description
            const description = document.createElement("p");

            description.textContent =
                task.description || "No description";

            description.style.marginBottom = "10px";

            // Task status
            const status = document.createElement("small");

            status.textContent = task.completed
                ? "✓ Completed"
                : "◷ Pending";

            status.style.color = task.completed
                ? "#19965b"
                : "#8052d6";

            status.style.fontWeight = "600";

            // Action buttons
            const actions = document.createElement("div");

            actions.style.display = "flex";
            actions.style.gap = "8px";
            actions.style.flexWrap = "wrap";
            actions.style.marginTop = "12px";

            // Complete / Pending button
            const completeButton = document.createElement("button");

            completeButton.textContent = task.completed
                ? "Mark Pending"
                : "Complete";

            completeButton.type = "button";

            // Edit button
            const editButton = document.createElement("button");

            editButton.textContent = "Edit";
            editButton.type = "button";

            // Delete button
            const deleteButton = document.createElement("button");

            deleteButton.textContent = "Delete";
            deleteButton.type = "button";

            [completeButton, editButton, deleteButton].forEach(button => {

                button.style.padding = "7px 12px";
                button.style.border = "none";
                button.style.borderRadius = "8px";
                button.style.cursor = "pointer";
                button.style.fontWeight = "600";

            });

            completeButton.style.background = "#e6fff1";
            completeButton.style.color = "#16834e";

            editButton.style.background = "#eee6ff";
            editButton.style.color = "#7141b8";

            deleteButton.style.background = "#ffe8ed";
            deleteButton.style.color = "#d13c61";

            // Button actions
            completeButton.addEventListener("click", function () {

                updateTask(task.id, {
                    title: task.title,
                    description: task.description || "",
                    completed: !task.completed
                });

            });

            editButton.addEventListener("click", function () {

                openEditTask(task);

            });

            deleteButton.addEventListener("click", function () {

                deleteTask(task.id);

            });

            actions.appendChild(completeButton);
            actions.appendChild(editButton);
            actions.appendChild(deleteButton);

            item.appendChild(title);
            item.appendChild(description);
            item.appendChild(status);
            item.appendChild(actions);

            taskList.appendChild(item);

        });

    } catch (error) {

        console.error("Task loading error:", error);

        showToast(error.message, "error");

    }

}


// =============================================
// CREATE OR EDIT TASK
// =============================================

taskForm.addEventListener("submit", async function (event) {

    event.preventDefault();

    const title = taskTitleInput.value.trim();

    const description = taskDescriptionInput.value.trim();

    if (!title) {

        showToast("Please enter a task title.", "error");

        return;

    }

    const taskData = {
        title: title,
        description: description,
        completed: false
    };

    try {

        const isEditing = editingTaskId !== null;

        const url = isEditing
            ? `${API_URL}/tasks/${editingTaskId}`
            : `${API_URL}/tasks`;

        const response = await fetch(url, {

            method: isEditing ? "PUT" : "POST",

            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },

            body: JSON.stringify(taskData)

        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Unable to save task.");
        }

        closeTaskModal();

        showToast(
            isEditing
                ? "Task updated successfully!"
                : "Task created successfully!"
        );

        await loadTasks();

    } catch (error) {

        console.error("Task saving error:", error);

        showToast(error.message, "error");

    }

});


// =============================================
// OPEN EDIT TASK
// =============================================

function openEditTask(task) {

    editingTaskId = task.id;

    taskTitleInput.value = task.title;

    taskDescriptionInput.value = task.description || "";

    taskModal.querySelector("h2").textContent = "Edit Your Task ✦";

    saveTaskButton.textContent = "Save Changes";

    taskModal.style.display = "flex";

}


// =============================================
// UPDATE TASK / CHANGE COMPLETION STATUS
// =============================================

async function updateTask(taskId, taskData) {

    try {

        const response = await fetch(`${API_URL}/tasks/${taskId}`, {

            method: "PUT",

            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },

            body: JSON.stringify(taskData)

        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Unable to update task.");
        }

        showToast("Task status updated successfully!");

        await loadTasks();

    } catch (error) {

        console.error("Task update error:", error);

        showToast(error.message, "error");

    }

}


// =============================================
// DELETE TASK
// =============================================

async function deleteTask(taskId) {

    try {

        const response = await fetch(`${API_URL}/tasks/${taskId}`, {

            method: "DELETE",

            headers: {
                "Authorization": `Bearer ${token}`
            }

        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Unable to delete task.");
        }

        showToast("Task deleted successfully!");

        await loadTasks();

    } catch (error) {

        console.error("Task deletion error:", error);

        showToast(error.message, "error");

    }

}

// =============================================
// CHRONEXA AI - COMPLETE SCHEDULE MANAGEMENT
// =============================================

let editingScheduleId = null;


// =============================================
// SCHEDULE POPUP ELEMENTS
// =============================================

const scheduleModal = document.getElementById("scheduleModal");
const scheduleForm = document.getElementById("scheduleForm");

const scheduleTitleInput = document.getElementById("scheduleTitle");
const scheduleDescriptionInput = document.getElementById("scheduleDescription");
const scheduleStartInput = document.getElementById("scheduleStartTime");
const scheduleEndInput = document.getElementById("scheduleEndTime");

const closeScheduleButton = document.getElementById("closeScheduleModal");
const cancelScheduleButton = document.getElementById("cancelScheduleBtn");

const saveScheduleButton = scheduleForm.querySelector(
    'button[type="submit"]'
);


// =============================================
// OPEN SCHEDULE POPUP
// =============================================

const scheduleCard = document.querySelector(".schedule-card");

function openScheduleModal() {

    editingScheduleId = null;

    scheduleForm.reset();

    document.getElementById("scheduleModalTitle").textContent =
        "Add New Schedule";

    saveScheduleButton.textContent = "Save Schedule";

    scheduleModal.style.display = "flex";
}


// Handle dynamically created Add Schedule buttons

scheduleCard.addEventListener("click", function (event) {

    if (event.target.closest(".small-create-btn")) {
        openScheduleModal();
    }

});


// =============================================
// CLOSE SCHEDULE POPUP
// =============================================

function closeScheduleModal() {

    scheduleModal.style.display = "none";

    scheduleForm.reset();

    editingScheduleId = null;
}

closeScheduleButton.addEventListener("click", closeScheduleModal);

cancelScheduleButton.addEventListener("click", closeScheduleModal);

scheduleModal.addEventListener("click", function (event) {

    if (event.target === scheduleModal) {
        closeScheduleModal();
    }

});


// =============================================
// LOAD AND DISPLAY SCHEDULES
// =============================================

async function loadSchedules() {

    const scheduleList = document.querySelector(".schedule-list");

    try {

        const schedules = await fetchDashboardData("/schedules");

        const scheduleCount = document.querySelector(".stat-blue h2");

        if (scheduleCount) {
            scheduleCount.textContent =
                String(schedules.length).padStart(2, "0");
        }

        if (!scheduleList) return;

        scheduleList.innerHTML = "";

        // Empty schedule message

        if (schedules.length === 0) {

            scheduleList.innerHTML = `
                <div class="empty-state">

                    <div class="empty-state-icon blue-icon">▣</div>

                    <h4>No schedules yet</h4>

                    <p>Your upcoming activities will appear here.</p>

                    <button type="button"
                        class="small-create-btn blue-btn">
                        + Add schedule
                    </button>

                </div>
            `;

            return;
        }

        // Add Schedule button

        const addButton = document.createElement("button");

        addButton.type = "button";
        addButton.className = "small-create-btn blue-btn";
        addButton.textContent = "+ Add schedule";

        scheduleList.appendChild(addButton);


        // Display schedules

        schedules.forEach(schedule => {

            const item = document.createElement("div");

            item.style.padding = "15px";
            item.style.marginBottom = "12px";
            item.style.borderRadius = "12px";
            item.style.background = "#f0f6ff";
            item.style.border = "1px solid #e0eaff";

            const title = document.createElement("h4");

            title.textContent =
                schedule.title || "Untitled schedule";

            const description = document.createElement("p");

            description.textContent =
                schedule.description || "No description";

            description.style.margin = "8px 0";


            const startDate = document.createElement("small");

            startDate.textContent =
                "Start: " +
                new Date(schedule.start_time).toLocaleString();

            startDate.style.display = "block";


            const endDate = document.createElement("small");

            endDate.textContent =
                "End: " +
                new Date(schedule.end_time).toLocaleString();

            endDate.style.display = "block";


            // Action buttons

            const actions = document.createElement("div");

            actions.style.display = "flex";
            actions.style.gap = "8px";
            actions.style.marginTop = "12px";


            const editButton = document.createElement("button");

            editButton.type = "button";
            editButton.textContent = "Edit";


            const deleteButton = document.createElement("button");

            deleteButton.type = "button";
            deleteButton.textContent = "Delete";


            [editButton, deleteButton].forEach(button => {

                button.style.padding = "7px 14px";
                button.style.border = "none";
                button.style.borderRadius = "8px";
                button.style.cursor = "pointer";
                button.style.fontWeight = "600";

            });

            editButton.style.background = "#eee6ff";
            editButton.style.color = "#7141b8";

            deleteButton.style.background = "#ffe8ed";
            deleteButton.style.color = "#d13c61";


            // Edit schedule

            editButton.addEventListener("click", function () {

                openEditSchedule(schedule);

            });


            // Delete schedule

            deleteButton.addEventListener("click", function () {

                deleteSchedule(schedule.id);

            });


            actions.appendChild(editButton);
            actions.appendChild(deleteButton);

            item.appendChild(title);
            item.appendChild(description);
            item.appendChild(startDate);
            item.appendChild(endDate);
            item.appendChild(actions);

            scheduleList.appendChild(item);

        });

    } catch (error) {

        console.error("Schedule loading error:", error);

        showToast(error.message, "error");

    }

}


// =============================================
// CREATE OR EDIT SCHEDULE
// =============================================

scheduleForm.addEventListener("submit", async function (event) {

    event.preventDefault();

    const title = scheduleTitleInput.value.trim();

    const description = scheduleDescriptionInput.value.trim();

    const startTime = scheduleStartInput.value;

    const endTime = scheduleEndInput.value;


    if (!title || !startTime || !endTime) {

        showToast("Please fill in all required fields.", "error");

        return;
    }


    if (new Date(endTime) <= new Date(startTime)) {

        showToast("End time must be after start time.", "error");

        return;
    }


    const scheduleData = {

        title: title,

        description: description,

        start_time: startTime,

        end_time: endTime

    };


    try {

        const isEditing = editingScheduleId !== null;

        const url = isEditing

            ? `${API_URL}/schedules/${editingScheduleId}`

            : `${API_URL}/schedules`;


        const response = await fetch(url, {

            method: isEditing ? "PUT" : "POST",

            headers: {

                "Content-Type": "application/json",

                "Authorization": `Bearer ${token}`

            },

            body: JSON.stringify(scheduleData)

        });


        const data = await response.json();

        if (!response.ok) {

            throw new Error(
                data.detail || "Unable to save schedule."
            );

        }


        closeScheduleModal();

        showToast(

            isEditing

                ? "Schedule updated successfully!"

                : "Schedule created successfully!"

        );

        await loadSchedules();

    } catch (error) {

        console.error("Schedule saving error:", error);

        showToast(error.message, "error");

    }

});


// =============================================
// EDIT SCHEDULE
// =============================================

function openEditSchedule(schedule) {

    editingScheduleId = schedule.id;

    scheduleTitleInput.value = schedule.title;

    scheduleDescriptionInput.value =
        schedule.description || "";

    scheduleStartInput.value =
        schedule.start_time.slice(0, 16);

    scheduleEndInput.value =
        schedule.end_time.slice(0, 16);


    document.getElementById("scheduleModalTitle").textContent =
        "Edit Schedule";

    saveScheduleButton.textContent = "Save Changes";

    scheduleModal.style.display = "flex";

}


// =============================================
// DELETE SCHEDULE
// =============================================

async function deleteSchedule(scheduleId) {

    try {

        const response = await fetch(
            `${API_URL}/schedules/${scheduleId}`,
            {

                method: "DELETE",

                headers: {

                    "Authorization": `Bearer ${token}`

                }

            }
        );


        const data = await response.json();

        if (!response.ok) {

            throw new Error(
                data.detail || "Unable to delete schedule."
            );

        }


        showToast("Schedule deleted successfully!");

        await loadSchedules();

    } catch (error) {

        console.error("Schedule deletion error:", error);

        showToast(error.message, "error");

    }

}
        
        
// =====================================
// NOTES MANAGEMENT
// =====================================

let editingNoteId = null;

const noteModal = document.getElementById("noteModal");
const noteForm = document.getElementById("noteForm");

const noteTitle = document.getElementById("noteTitle");
const noteContent = document.getElementById("noteContent");

const noteModalTitle = document.getElementById("noteModalTitle");
const saveNoteBtn = document.getElementById("saveNoteBtn");

const closeNoteModal = document.getElementById("closeNoteModal");
const cancelNoteBtn = document.getElementById("cancelNoteBtn");


// OPEN NOTES POPUP
function openNoteModal() {

    editingNoteId = null;

    noteForm.reset();

    noteModalTitle.textContent = "Add New Note";
    saveNoteBtn.textContent = "Save Note";

    noteModal.style.display = "flex";
}


// CLOSE NOTES POPUP
function closeNotePopup() {

    noteModal.style.display = "none";

    noteForm.reset();

    editingNoteId = null;
}


// ADD NOTE BUTTON
document.querySelector(".notes-card").addEventListener("click", function(event) {

    if (event.target.closest(".note-create-btn")) {

        openNoteModal();

    }

});


// CLOSE BUTTONS
closeNoteModal.addEventListener("click", closeNotePopup);

cancelNoteBtn.addEventListener("click", closeNotePopup);


// CLOSE WHEN CLICKING OUTSIDE
noteModal.addEventListener("click", function(event) {

    if (event.target === noteModal) {

        closeNotePopup();

    }

});


// LOAD AND DISPLAY NOTES
async function loadNotes() {

    const notesCard = document.querySelector(".notes-card");

    try {

        const notes = await fetchDashboardData("/notes");

        const noteCount = document.querySelector(".stat-pink h2");

        if (noteCount) {

            noteCount.textContent =
                String(notes.length).padStart(2, "0");

        }

        if (!notesCard) return;

        const oldList = notesCard.querySelector(".note-list");

        if (oldList) oldList.remove();

        const noteList = document.createElement("div");

        noteList.className = "note-list";

        if (notes.length === 0) {

            noteList.innerHTML = `
                <div class="note-empty">
                    <span>✎</span>
                    <p>No notes available yet.</p>

                    <button class="small-create-btn note-create-btn">
                        + Add a note
                    </button>
                </div>
            `;

        } else {

            notes.forEach(note => {

                const item = document.createElement("div");

                item.style.padding = "14px";
                item.style.marginBottom = "10px";
                item.style.background = "#fff4fa";
                item.style.borderRadius = "12px";

                const title = document.createElement("h4");
                title.textContent = note.title || "Untitled note";

                const content = document.createElement("p");
                content.textContent = note.content || "No content";

                const actions = document.createElement("div");
                actions.style.display = "flex";
                actions.style.gap = "10px";
                actions.style.marginTop = "12px";

                const editBtn = document.createElement("button");
                editBtn.type = "button";
                editBtn.textContent = "Edit";
                editBtn.className = "small-create-btn";

                editBtn.addEventListener("click", function() {

                    editingNoteId = note.id;

                    noteTitle.value = note.title || "";
                    noteContent.value = note.content || "";

                    noteModalTitle.textContent = "Edit Note";
                    saveNoteBtn.textContent = "Update Note";

                    noteModal.style.display = "flex";

                });

                const deleteBtn = document.createElement("button");
                deleteBtn.type = "button";
                deleteBtn.textContent = "Delete";
                deleteBtn.className = "small-create-btn";
                deleteBtn.style.background = "#ffe8ed";
                deleteBtn.style.color = "#c0395a";

                deleteBtn.addEventListener("click", function() {

                    deleteNote(note.id);

                });

                actions.appendChild(editBtn);
                actions.appendChild(deleteBtn);

                item.appendChild(title);
                item.appendChild(content);
                item.appendChild(actions);

                noteList.appendChild(item);

            });

            const addButton = document.createElement("button");

            addButton.type = "button";
            addButton.className = "small-create-btn note-create-btn";
            addButton.textContent = "+ Add a note";

            noteList.appendChild(addButton);

        }

        notesCard.appendChild(noteList);

    } catch (error) {

        console.error("Notes loading error:", error);

    }

}


// SAVE OR UPDATE NOTE
noteForm.addEventListener("submit", async function(event) {

    event.preventDefault();

    const title = noteTitle.value.trim();
    const content = noteContent.value.trim();

    if (!title || !content) {

        showToast("Please fill in all note fields.", "error");
        return;

    }

    const token = sessionStorage.getItem("access_token");

    const url = editingNoteId
        ? `${API_URL}/notes/${editingNoteId}`
        : `${API_URL}/notes`;

    try {

        const response = await fetch(url, {

            method: editingNoteId ? "PUT" : "POST",

            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },

            body: JSON.stringify({
                title: title,
                content: content
            })

        });

        const data = await response.json();

        if (!response.ok) {

            throw new Error(data.detail || "Unable to save note.");

        }

        closeNotePopup();

        showToast(
            editingNoteId
                ? "Note updated successfully!"
                : "Note created successfully!"
        );

        await loadNotes();

    } catch (error) {

        console.error("Note saving error:", error);

        showToast(error.message || "Unable to save note.", "error");

    }

});


// DELETE NOTE
async function deleteNote(noteId) {

    const token = sessionStorage.getItem("access_token");

    try {

        const response = await fetch(`${API_URL}/notes/${noteId}`, {

            method: "DELETE",

            headers: {
                "Authorization": `Bearer ${token}`
            }

        });

        const data = await response.json();

        if (!response.ok) {

            throw new Error(data.detail || "Unable to delete note.");

        }

        showToast("Note deleted successfully!");

        await loadNotes();

    } catch (error) {

        console.error("Note deletion error:", error);

        showToast(error.message || "Unable to delete note.", "error");

    }

}

      
// =====================================
// LOAD REMINDERS
// =====================================

async function loadReminders() {

    try {

        const reminders =
            await fetchDashboardData("/reminders");

        // Update reminder count
        const reminderCount =
            document.querySelector(".stat-orange h2");

        if (reminderCount) {
            reminderCount.textContent =
                String(reminders.length).padStart(2, "0");
        }

        // Display reminders
        const reminderList =
            document.querySelector(".reminder-list");

        if (!reminderList) return;

        reminderList.innerHTML = "";

        // Empty state
        if (reminders.length === 0) {

            reminderList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">♧</div>
                    <h4>No reminders yet</h4>
                    <p>Your upcoming reminders will appear here.</p>
                    <button class="small-create-btn reminder-create-btn">
                        + Create a reminder
                    </button>
                </div>
            `;

            return;
        }

        // Display reminder cards
        reminders.forEach(reminder => {

            const reminderCard =
                document.createElement("div");

            reminderCard.className = "reminder-item";

            const reminderDate =
                new Date(reminder.remind_at).toLocaleString();

            reminderCard.innerHTML = `
                <div class="reminder-details">
                    <h4>${reminder.title}</h4>
                    <p>${reminder.description || ""}</p>
                    <span>⏰ ${reminderDate}</span>
                </div>

                <div class="reminder-actions">
                    <button class="edit-reminder-btn"
                        data-id="${reminder.id}">
                        Edit
                    </button>

                    <button class="delete-reminder-btn"
                        data-id="${reminder.id}">
                        Delete
                    </button>
                </div>
            `;

            reminderList.appendChild(reminderCard);

        });

    } catch (error) {

        console.error("Reminder loading error:", error);

    }

}
        // =====================================
        // REMINDER MANAGEMENT
        // =====================================

        let editingReminderId = null;

        const reminderModal =
            document.getElementById("reminderModal");

        const reminderForm =
            document.getElementById("reminderForm");

        const reminderModalTitle =
            document.getElementById("reminderModalTitle");

        const reminderTitle =
            document.getElementById("reminderTitle");

        const reminderDescription =
            document.getElementById("reminderDescription");

        const reminderTime =
            document.getElementById("reminderTime");


        // OPEN ADD REMINDER POPUP

        function openReminderModal() {

            editingReminderId = null;

            reminderForm.reset();

            reminderModalTitle.textContent =
                "Add New Reminder";

            reminderModal.style.display = "flex";

        }


        // CLOSE REMINDER POPUP

        function closeReminderModal() {

            reminderModal.style.display = "none";

            reminderForm.reset();

            editingReminderId = null;

        }


        // ADD REMINDER BUTTONS

        document.querySelectorAll(".reminder-create-btn")
            .forEach(button => {

                button.addEventListener("click", openReminderModal);

            });


        // CLOSE BUTTON

        document.getElementById("closeReminderModal")
            .addEventListener("click", closeReminderModal);


        // CANCEL BUTTON

        document.getElementById("cancelReminderBtn")
            .addEventListener("click", closeReminderModal);


        // SAVE OR UPDATE REMINDER

        reminderForm.addEventListener("submit", async function(event) {

            event.preventDefault();

            const reminderData = {

                title: reminderTitle.value.trim(),

                description: reminderDescription.value.trim(),

                remind_at: reminderTime.value

            };

            try {

                const token =
                    sessionStorage.getItem("access_token");

                const url = editingReminderId
                    ? `${API_URL}/reminders/${editingReminderId}`
                    : `${API_URL}/reminders`;

                const response = await fetch(url, {

                    method: editingReminderId ? "PUT" : "POST",

                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${token}`
                    },

                    body: JSON.stringify(reminderData)

                });

                if (!response.ok) {

                    const errorData = await response.json();

                    throw new Error(
                        errorData.detail || "Unable to save reminder"
                    );

                }

                showToast(
                    editingReminderId
                        ? "Reminder updated successfully!"
                        : "Reminder created successfully!"
                );

                closeReminderModal();

                loadReminders();

            } catch (error) {

                console.error("Reminder save error:", error);

                showToast(error.message, "error");

            }

        });
        

         // =====================================
        // EDIT REMINDER
        // =====================================

        async function editReminder(reminderId) {

            try {

                const reminders =
                    await fetchDashboardData("/reminders");

                const reminder = reminders.find(
                    item => item.id === Number(reminderId)
                );

                if (!reminder) {
                    showToast("Reminder not found", "error");
                    return;
                }

                editingReminderId = reminder.id;

                reminderTitle.value = reminder.title;

                reminderDescription.value =
                    reminder.description || "";

                const date = new Date(reminder.remind_at);

                const localDate = new Date(
                    date.getTime() - date.getTimezoneOffset() * 60000
                ).toISOString().slice(0, 16);

                reminderTime.value = localDate;

                reminderModalTitle.textContent =
                    "Edit Reminder";

                reminderModal.style.display = "flex";

            } catch (error) {

                console.error("Edit reminder error:", error);

                showToast("Unable to open reminder", "error");

            }

        }


        // =====================================
// DELETE REMINDER
// =====================================

async function deleteReminder(reminderId) {

    try {

        const token =
            sessionStorage.getItem("access_token");

        const response = await fetch(
            `${API_URL}/reminders/${reminderId}`,
            {
                method: "DELETE",
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            }
        );

        if (!response.ok) {
            throw new Error("Unable to delete reminder");
        }

        showToast("Reminder deleted successfully!");

        loadReminders();

    } catch (error) {

        console.error("Delete reminder error:", error);

        showToast(error.message, "error");

    }

}

// =====================================
// REMINDER BUTTON EVENTS
// =====================================

document.addEventListener("click", function(event) {

    const editButton =
        event.target.closest(".edit-reminder-btn");

    const deleteButton =
        event.target.closest(".delete-reminder-btn");

    if (editButton) {

        editReminder(editButton.dataset.id);

    }

    if (deleteButton) {

        deleteReminder(deleteButton.dataset.id);

    }

});

// =====================================
// AUTOMATIC BROWSER REMINDER CHECKER
// =====================================

async function checkBrowserReminders() {

    if (!("Notification" in window)) {
        return;
    }

    if (Notification.permission !== "granted") {
        return;
    }

    try {

        const reminders = await fetchDashboardData("/reminders");

        if (!Array.isArray(reminders)) {
            return;
        }

        const notifiedIds = JSON.parse(
            sessionStorage.getItem("chronexaNotifiedReminders") || "[]"
        );

        const currentTime = new Date();

        reminders.forEach(reminder => {

            const reminderTime = new Date(reminder.remind_at);

            if (
                reminderTime <= currentTime &&
                !notifiedIds.includes(reminder.id)
            ) {

                new Notification("Chronexa AI Reminder", {
                    body: reminder.title +
                        (reminder.description
                            ? "\n" + reminder.description
                            : ""),
                    icon: "https://cdn-icons-png.flaticon.com/512/1827/1827370.png"
                });

                showToast("Reminder: " + reminder.title);

                notifiedIds.push(reminder.id);
            }

        });

        sessionStorage.setItem(
            "chronexaNotifiedReminders",
            JSON.stringify(notifiedIds)
        );

    } catch (error) {

        console.error("Browser reminder notification error:", error);

    }

}


// =====================================
// START REMINDER NOTIFICATION CHECKER
// =====================================

function startReminderNotifications() {

    checkBrowserReminders();

    setInterval(checkBrowserReminders, 30000);

}

// =====================================
// LOAD ALL DASHBOARD DATA
// =====================================

loadTasks();

loadSchedules();

loadNotes();

loadReminders();

// Start automatic browser reminder checking
startReminderNotifications();

}
}

// =====================================
// CHRONEXA AI - CHAT INTERFACE
// =====================================

const aiChatInput = document.getElementById("aiChatInput");
const aiChatMessages = document.getElementById("aiChatMessages");
const aiSendBtn = document.getElementById("aiSendBtn");

function sendAIChatMessage() {

    if (!aiChatInput || !aiChatMessages) {
        return;
    }

    const message = aiChatInput.value.trim();

    if (!message) {
        return;
    }

    // Display user message
    const userMessage = document.createElement("div");

    userMessage.className = "ai-message ai-message-user";
    userMessage.textContent = message;

    aiChatMessages.appendChild(userMessage);

    // Clear input
    aiChatInput.value = "";

    // Temporary response until AI backend is connected
    const botMessage = document.createElement("div");

    botMessage.className = "ai-message ai-message-bot";
    botMessage.textContent =
        "Thanks for your message! My AI connection is coming soon.";

    aiChatMessages.appendChild(botMessage);

    // Scroll to latest message
    aiChatMessages.scrollTop = aiChatMessages.scrollHeight;
}


// Send button
if (aiSendBtn) {
    aiSendBtn.addEventListener("click", sendAIChatMessage);
}


// Enter key
if (aiChatInput) {
    aiChatInput.addEventListener("keydown", function(event) {

        if (event.key === "Enter") {
            sendAIChatMessage();
        }

    });
}
