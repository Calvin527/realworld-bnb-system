INSERT INTO users (full_name, email, phone, password_hash, role, is_verified, is_active)
VALUES
('System Administrator', 'admin@sunrisebnb.local', '0123456789',
 'scrypt:32768:8:1$WvP6xcT4o4fmstMo$b2c9872f3efdb931077e4be2dd3ad3fbf2631d223edeece364969cf61019519b773c97f9ce9374cb8aad4fd33d734add2a1edbf7727eb1f70130d9f8717276b7', 'admin', TRUE, TRUE),
('Demo Guest', 'guest@example.com', '0712345678',
 'scrypt:32768:8:1$g6BLaLdn1ll4oefD$7f7b03a4fcd24da5e83580e296ff0eb127a45f1f1302f29cdb908d490dc0f78b10c2ea1655172a8590ed58d27d91dc6d70c2520b4bebc20cc72867a267d9604c', 'user', TRUE, TRUE);

INSERT INTO rooms (room_name, room_type, capacity, price_per_night, description, image_url) VALUES
('Sunrise Suite', 'Deluxe', 2, 950.00, 'Large deluxe suite with en-suite bathroom and garden view.', 'https://images.unsplash.com/photo-1566665797739-1674de7a421a?auto=format&fit=crop&w=1000&q=80'),
('Family Nest', 'Family', 4, 1450.00, 'Spacious family room with two beds and breakfast-friendly dining area.', 'https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=1000&q=80'),
('Budget Comfort', 'Standard', 2, 650.00, 'Affordable room with comfortable bedding and Wi-Fi.', 'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=1000&q=80');

INSERT INTO breakfast_options (name, description, price) VALUES
('Continental Breakfast', 'Tea/coffee, fruit, toast, croissant, and yoghurt.', 95.00),
('Full English Breakfast', 'Eggs, bacon, sausage, grilled tomato, toast, and juice.', 145.00),
('Healthy Breakfast Bowl', 'Granola, yoghurt, honey, seasonal fruit, and herbal tea.', 110.00);
