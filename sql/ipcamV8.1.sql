CREATE TABLE Admin (
    admin_id INT PRIMARY KEY,
    admin_password VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    token TEXT
);
CREATE TABLE Users (
    user_id INT PRIMARY KEY, 
    line_id VARCHAR(33) NOT NULL,
    message_line_id VARCHAR(33) DEFAULT NULL,
    user_name VARCHAR(20),      
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    token TEXT
);
CREATE TABLE Cameras (
    camera_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    camera_name VARCHAR(20),
    brand VARCHAR(20) NOT NULL,
    Model VARCHAR(20) NOT NULL,
    ip_address VARCHAR(27),
    camera_username VARCHAR(20),
    camera_password VARCHAR(20),
    rtsp_url TEXT,
    device_id CHAR(36) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (device_id) REFERENCES Devices(device_id)
);
CREATE TABLE Devices (
    device_id CHAR(36) PRIMARY KEY,
    user_id INT,
    Manufacture_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    Model VARCHAR(10) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);
CREATE TABLE Projects (
    project_id INT AUTO_INCREMENT PRIMARY KEY,
    project_name VARCHAR(20) NOT NULL,
    camera_id INT,
    user_id INT,
    device_id CHAR(36),
    start_time JSON NOT NULL,
    status VARCHAR(1) NOT NULL,  
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,                             
    FOREIGN KEY (camera_id) REFERENCES Cameras(camera_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (device_id) REFERENCES Devices(device_id)
);
CREATE TABLE Models (
    model_id INT AUTO_INCREMENT PRIMARY KEY,
    model_name VARCHAR(20) NOT NULL,
    model_version VARCHAR(20),
    event_type VARCHAR(25),
    model_path TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE Events (
    event_id INT AUTO_INCREMENT PRIMARY KEY,
    event_name VARCHAR(20) NOT NULL,
    model_id INT,
    FOREIGN KEY (model_id) REFERENCES Models(model_id)
);
CREATE TABLE ModelProjectRelations (
    model_id INT,
    project_id INT,
    PRIMARY KEY (model_id, project_id),
    FOREIGN KEY (model_id) REFERENCES Models(model_id),
    FOREIGN KEY (project_id) REFERENCES Projects(project_id)ON DELETE CASCADE
);
CREATE TABLE EventProjectRelations (
    event_id INT,
    project_id INT,
    notification_content TEXT NOT NULL,
    PRIMARY KEY (event_id, project_id),
    FOREIGN KEY (event_id) REFERENCES Events(event_id),
    FOREIGN KEY (project_id) REFERENCES Projects(project_id)ON DELETE CASCADE
);
CREATE TABLE Contacts (
    contact_id INT,
    user_id INT,
    contact_name VARCHAR(20),
    PRIMARY KEY (contact_id, user_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);
CREATE TABLE ContactProjectRelations (
    contact_id INT,
    project_id INT,
    PRIMARY KEY (contact_id, project_id),
    FOREIGN KEY (contact_id) REFERENCES Contacts(contact_id),
    FOREIGN KEY (project_id) REFERENCES Projects(project_id)ON DELETE CASCADE
);
CREATE TABLE AbnormalEvents (
    abnormal_id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT,
    event_id INT,
    picture_url TEXT,
    occurred_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES Projects(project_id) ON DELETE CASCADE,
    FOREIGN KEY (event_id) REFERENCES Events(event_id)
);
INSERT INTO Admin(admin_id)
VALUE(2);
INSERT INTO Devices(device_id, user_id, Model)
VALUES (UUID(), NULL,'v1.1'),(UUID(), NULL,'v1.1'),(UUID(), NULL,'v1.1'),(UUID(), NULL,'v1.1')
