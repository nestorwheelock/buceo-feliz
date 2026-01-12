"""Management command to seed blog categories and posts for Happy Diving."""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from django_cms_core.models import (
    BlogCategory,
    ContentPage,
    AccessLevel,
    PageStatus,
    PageType,
)
from django_cms_core.services import add_block, publish_page
from django_parties.models import Person


User = get_user_model()


CATEGORIES = [
    {
        "name": "Dive Destinations",
        "slug": "destinations",
        "description": "Explore the world's best diving locations, from tropical reefs to cold water adventures.",
        "color": "#0EA5E9",  # Sky blue
        "sort_order": 1,
    },
    {
        "name": "Gear & Equipment",
        "slug": "gear",
        "description": "Reviews, tips, and guides for scuba diving equipment and accessories.",
        "color": "#8B5CF6",  # Purple
        "sort_order": 2,
    },
    {
        "name": "Training & Certification",
        "slug": "training",
        "description": "Everything about dive training, certifications, and improving your skills.",
        "color": "#10B981",  # Emerald
        "sort_order": 3,
    },
    {
        "name": "Marine Life",
        "slug": "marine-life",
        "description": "Discover the fascinating creatures that inhabit our oceans.",
        "color": "#F59E0B",  # Amber
        "sort_order": 4,
    },
    {
        "name": "Safety & Health",
        "slug": "safety",
        "description": "Important information about dive safety, health considerations, and best practices.",
        "color": "#EF4444",  # Red
        "sort_order": 5,
    },
    {
        "name": "Conservation",
        "slug": "conservation",
        "description": "Ocean conservation efforts and how divers can help protect marine ecosystems.",
        "color": "#22C55E",  # Green
        "sort_order": 6,
    },
    {
        "name": "Dive Stories",
        "slug": "stories",
        "description": "Personal dive experiences, adventures, and memorable underwater moments.",
        "color": "#EC4899",  # Pink
        "sort_order": 7,
    },
]


POSTS = [
    {
        "slug": "top-10-dive-sites-cozumel",
        "title": "Top 10 Dive Sites in Cozumel You Can't Miss",
        "category_slug": "destinations",
        "excerpt": "Discover the best underwater adventures Cozumel has to offer, from dramatic wall dives to colorful reef gardens teeming with marine life.",
        "featured_image_url": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=1200",
        "reading_time_minutes": 8,
        "tags": ["cozumel", "mexico", "caribbean", "wall diving", "reef"],
        "blocks": [
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>Cozumel, Mexico, is consistently ranked among the world's top dive destinations, and for good reason. With crystal-clear waters, dramatic wall dives, and an incredible variety of marine life, this Caribbean island offers something for divers of every skill level.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "1. Palancar Reef", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>Perhaps the most famous dive site in Cozumel, Palancar Reef is actually a series of dive sites along a massive reef system. The towering coral formations, swim-throughs, and abundant marine life make this a must-dive destination. Look for eagle rays, sea turtles, and the occasional nurse shark.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "2. Santa Rosa Wall", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>For experienced divers, Santa Rosa Wall offers one of the most exhilarating drift dives in the Caribbean. The wall drops from 50 feet to well beyond recreational limits, featuring massive sponges, black coral, and deep overhangs perfect for exploring.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "3. Columbia Deep", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>Home to some of the largest coral pinnacles in Cozumel, Columbia Deep is where you'll find stunning formations rising from 80-100 feet. The area is known for encounters with spotted eagle rays and large groupers.</p>"
                },
            },
            {
                "type": "call_to_action",
                "data": {
                    "title": "Ready to Dive Cozumel?",
                    "text": "Book your Cozumel diving adventure with us today!",
                    "button_text": "View Excursions",
                    "button_url": "/excursions/",
                },
            },
        ],
    },
    {
        "slug": "choosing-first-wetsuit",
        "title": "How to Choose Your First Wetsuit: A Complete Guide",
        "category_slug": "gear",
        "excerpt": "Everything you need to know about selecting the right wetsuit for your diving needs, from thickness and material to fit and features.",
        "featured_image_url": "https://images.unsplash.com/photo-1682687220742-aba13b6e50ba?w=1200",
        "reading_time_minutes": 6,
        "tags": ["wetsuit", "gear", "beginners", "equipment", "thermal protection"],
        "blocks": [
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>A wetsuit is one of the most important pieces of diving equipment you'll own. It keeps you warm, protects you from stings and scrapes, and can even add buoyancy. But with so many options available, how do you choose the right one?</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "Understanding Wetsuit Thickness", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<ul><li><strong>3mm</strong> - Warm tropical waters (80°F/27°C and above)</li><li><strong>5mm</strong> - Temperate waters (68-80°F/20-27°C)</li><li><strong>7mm</strong> - Cold water diving (50-68°F/10-20°C)</li><li><strong>Semi-dry or Drysuit</strong> - Very cold water (below 50°F/10°C)</li></ul>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "Getting the Right Fit", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>A properly fitting wetsuit should be snug but not restrictive. Water should not flow freely through the suit, but you should still be able to move and breathe comfortably. Here are key fit points to check:</p><ul><li>No gaps at the neck, wrists, or ankles</li><li>Smooth contact across the back with no air pockets</li><li>Full range of motion in arms and legs</li><li>Comfortable when bending at waist and knees</li></ul>"
                },
            },
        ],
    },
    {
        "slug": "open-water-certification-guide",
        "title": "Your Complete Guide to Open Water Certification",
        "category_slug": "training",
        "excerpt": "Everything you need to know about getting your Open Water diving certification, from choosing an agency to what to expect during the course.",
        "featured_image_url": "https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=1200",
        "reading_time_minutes": 10,
        "tags": ["certification", "padi", "ssi", "open water", "beginners", "training"],
        "blocks": [
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>Getting your Open Water certification is your ticket to exploring the underwater world. This certification allows you to dive independently with a buddy to depths of 18 meters (60 feet) anywhere in the world. Here's everything you need to know about the process.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "Choosing a Certification Agency", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>The two most popular certification agencies are <strong>PADI</strong> (Professional Association of Diving Instructors) and <strong>SSI</strong> (Scuba Schools International). Both are recognized worldwide and offer comparable training. The choice often comes down to which agency your local dive shop is affiliated with.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "Course Structure", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>The Open Water course typically includes:</p><ul><li><strong>Knowledge Development</strong> - Online or classroom learning covering dive theory</li><li><strong>Confined Water Dives</strong> - Pool sessions to practice skills in controlled environment</li><li><strong>Open Water Dives</strong> - 4 dives in open water demonstrating mastery of skills</li></ul>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "Prerequisites", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>To enroll in an Open Water course, you must:</p><ul><li>Be at least 10 years old (Junior Open Water) or 15 years old (Open Water)</li><li>Be comfortable in the water and able to swim</li><li>Complete a medical questionnaire (some conditions require physician clearance)</li></ul>"
                },
            },
        ],
    },
    {
        "slug": "sea-turtle-encounters",
        "title": "Sea Turtle Encounters: A Diver's Guide to These Gentle Giants",
        "category_slug": "marine-life",
        "excerpt": "Learn about the different species of sea turtles you might encounter while diving, their behaviors, and how to observe them responsibly.",
        "featured_image_url": "https://images.unsplash.com/photo-1591025207163-942350e47db2?w=1200",
        "reading_time_minutes": 7,
        "tags": ["sea turtles", "marine life", "wildlife", "conservation", "underwater photography"],
        "blocks": [
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>Few underwater encounters are as magical as coming face-to-face with a sea turtle. These ancient mariners have been swimming our oceans for over 100 million years, and as divers, we have the privilege of sharing their underwater world.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "Species You Might Encounter", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p><strong>Green Sea Turtle</strong> - The most commonly encountered species, named for the green color of their fat. Often seen grazing on seagrass beds.</p><p><strong>Hawksbill Turtle</strong> - Recognizable by their pointed beak and beautiful patterned shell. Frequently found on coral reefs feeding on sponges.</p><p><strong>Loggerhead Turtle</strong> - Named for their large heads, these powerful swimmers are often seen in temperate waters.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "Responsible Turtle Watching", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<ul><li>Keep a respectful distance of at least 2 meters (6 feet)</li><li>Never touch, chase, or ride sea turtles</li><li>Avoid blocking their path to the surface - they need to breathe!</li><li>Don't use flash photography</li><li>Let them approach you rather than swimming after them</li></ul>"
                },
            },
        ],
    },
    {
        "slug": "understanding-dcs",
        "title": "Understanding Decompression Sickness: Prevention and Recognition",
        "category_slug": "safety",
        "excerpt": "A comprehensive guide to decompression sickness (the bends), including risk factors, symptoms, prevention strategies, and what to do if you suspect DCS.",
        "featured_image_url": "https://images.unsplash.com/photo-1544551763-77ef2d0cfc6c?w=1200",
        "reading_time_minutes": 9,
        "tags": ["safety", "dcs", "decompression", "health", "emergency"],
        "blocks": [
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>Decompression sickness (DCS), commonly known as \"the bends,\" is one of the most serious risks divers face. Understanding what causes it, how to prevent it, and how to recognize symptoms is essential knowledge for every diver.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "What Causes DCS?", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>During a dive, nitrogen from the air we breathe dissolves into our body tissues under pressure. If we ascend too quickly, this nitrogen can form bubbles in our tissues and bloodstream, similar to how bubbles form when opening a carbonated drink. These bubbles can cause a range of symptoms from mild joint pain to life-threatening neurological damage.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "Prevention Strategies", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<ul><li>Always follow your dive computer or tables</li><li>Ascend slowly - no faster than 30 feet (9m) per minute</li><li>Perform safety stops at 15 feet (5m) for 3-5 minutes</li><li>Stay well hydrated before and after diving</li><li>Avoid flying within 18-24 hours after diving</li><li>Don't push no-decompression limits</li></ul>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "Recognizing Symptoms", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>Symptoms can appear immediately or up to 24 hours after diving:</p><ul><li>Joint pain (especially shoulders, elbows, knees)</li><li>Fatigue or unusual tiredness</li><li>Skin rash or itching</li><li>Dizziness or vertigo</li><li>Numbness or tingling</li><li>Difficulty breathing</li></ul><p><strong>If you suspect DCS, seek emergency medical care immediately and contact DAN (Divers Alert Network).</strong></p>"
                },
            },
        ],
    },
    {
        "slug": "coral-reef-conservation",
        "title": "Coral Reef Conservation: How Divers Can Make a Difference",
        "category_slug": "conservation",
        "excerpt": "Discover the threats facing coral reefs worldwide and learn practical ways you can help protect these vital ecosystems as a diver.",
        "featured_image_url": "https://images.unsplash.com/photo-1546026423-cc4642628d2b?w=1200",
        "reading_time_minutes": 8,
        "tags": ["conservation", "coral reef", "environment", "sustainability", "ocean health"],
        "blocks": [
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>Coral reefs cover less than 1% of the ocean floor but support approximately 25% of all marine species. As divers, we have a unique connection to these underwater ecosystems and a responsibility to help protect them for future generations.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "Threats to Coral Reefs", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>Coral reefs face numerous threats, both local and global:</p><ul><li><strong>Climate Change</strong> - Rising ocean temperatures cause coral bleaching</li><li><strong>Ocean Acidification</strong> - Absorbed CO2 makes it harder for corals to build skeletons</li><li><strong>Pollution</strong> - Runoff from agriculture and urban areas</li><li><strong>Overfishing</strong> - Disrupts reef ecosystem balance</li><li><strong>Physical Damage</strong> - Anchor damage, careless divers, and destructive fishing practices</li></ul>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "How Divers Can Help", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<ul><li><strong>Perfect Your Buoyancy</strong> - Good buoyancy control prevents accidental reef contact</li><li><strong>Choose Reef-Safe Sunscreen</strong> - Avoid oxybenzone and octinoxate</li><li><strong>Participate in Reef Cleanups</strong> - Remove debris and fishing line</li><li><strong>Report Marine Life Sightings</strong> - Citizen science helps researchers track reef health</li><li><strong>Support Conservation Organizations</strong> - Donate to or volunteer with reef protection groups</li><li><strong>Spread Awareness</strong> - Share your underwater experiences and educate others</li></ul>"
                },
            },
        ],
    },
    {
        "slug": "night-dive-encounter-with-octopus",
        "title": "My Unforgettable Night Dive Encounter with a Giant Pacific Octopus",
        "category_slug": "stories",
        "excerpt": "A personal account of an extraordinary night dive in the Pacific Northwest and an unexpected encounter with one of the ocean's most intelligent creatures.",
        "featured_image_url": "https://images.unsplash.com/photo-1545671913-b89ac1b4ac10?w=1200",
        "reading_time_minutes": 5,
        "tags": ["night diving", "octopus", "pacific northwest", "personal story", "adventure"],
        "blocks": [
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>It was a cold February evening when I slipped beneath the dark waters of Puget Sound. Night diving in the Pacific Northwest isn't for everyone - the water temperature hovered around 45°F (7°C), and visibility after sunset can be unpredictable. But something kept drawing me back to these waters, and on this particular night, I would discover why.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "The Descent", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>My dive buddy and I descended along the rocky wall, our primary lights cutting narrow paths through the darkness. The beam revealed sleeping rockfish tucked into crevices and tiny shrimp whose eyes reflected our lights like scattered stars. At about 40 feet, something unusual caught my attention - a subtle movement in the rocks that didn't match the gentle surge.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "The Encounter", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>I swept my light across the area and there she was - a Giant Pacific Octopus, easily five feet from arm tip to arm tip, watching me with those remarkable, intelligent eyes. Instead of retreating into her den, she seemed curious, extending one arm toward my light while the others remained anchored to the rocks.</p><p>For nearly twenty minutes, we observed each other. She changed colors constantly - from deep red to mottled brown to almost white - and at one point reached out to touch my gloved hand with a single exploring arm. The suckers gripped briefly before releasing, as if testing whether I was friend or food (or perhaps just confused).</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "A Lasting Impression", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>That encounter changed how I think about diving and marine life. These creatures aren't just animals to photograph or check off a list - they're individuals with their own curiosity and intelligence. Every dive now feels like an opportunity for connection, a chance to be a guest in someone else's world.</p><p>If you ever get the chance to night dive in the Pacific Northwest, take it. You never know who you might meet in the darkness.</p>"
                },
            },
        ],
    },
    {
        "slug": "cenote-diving-yucatan",
        "title": "Cenote Diving in the Yucatan: An Underground Adventure",
        "category_slug": "destinations",
        "excerpt": "Explore the mystical underwater caves of Mexico's Yucatan Peninsula, where crystal-clear freshwater, ancient formations, and Mayan history converge.",
        "featured_image_url": "https://images.unsplash.com/photo-1682687220742-aba13b6e50ba?w=1200",
        "reading_time_minutes": 7,
        "tags": ["cenotes", "mexico", "cave diving", "cavern diving", "freshwater"],
        "blocks": [
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>Beneath the jungle floor of Mexico's Yucatan Peninsula lies one of the world's most extensive underwater cave systems. These cenotes - natural sinkholes filled with crystal-clear freshwater - offer divers an experience unlike anything else on Earth.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "What is a Cenote?", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>Cenotes formed over millions of years as rainwater dissolved the limestone bedrock, creating vast underground river systems. When cave ceilings collapsed, they created the open pools we see today. The ancient Maya considered cenotes sacred - gateways to the underworld - and many contain archaeological artifacts.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "Top Cenotes for Divers", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p><strong>Dos Ojos</strong> - Famous for its two connected caverns with spectacular light effects. Perfect for Open Water divers.</p><p><strong>The Pit</strong> - A stunning 390-foot deep sinkhole with dramatic halocline effects and ancient tree remains.</p><p><strong>Gran Cenote</strong> - Beautiful formations and excellent visibility, ideal for first-time cenote divers.</p><p><strong>Angelita</strong> - Features a ghostly \"underwater river\" created by a hydrogen sulfide cloud at 100 feet.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "Certification Requirements", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>Most cenote dives fall into two categories:</p><ul><li><strong>Cavern Diving</strong> - Stays within the light zone, Open Water certification required. Natural light always visible.</li><li><strong>Cave Diving</strong> - Penetrates beyond natural light. Requires specialized cave diving certification and equipment.</li></ul><p>Always dive with a certified cenote guide - these environments require specific knowledge of the systems.</p>"
                },
            },
        ],
    },
    # === Posts from nestorwheelock.com (rewritten for Happy Diving) ===
    {
        "slug": "shore-dive-ojo-de-agua-puerto-morelos",
        "title": "Shore Diving at Ojo de Agua: Puerto Morelos' Hidden Gem",
        "category_slug": "stories",
        "excerpt": "Discover the magic of Ojo de Agua, where freshwater springs create a dancing halocline and recovering reefs showcase nature's resilience.",
        "featured_image_url": "https://nestorwheelock.com/media/library/2024/12/PC220002.jpg",
        "reading_time_minutes": 6,
        "tags": ["shore diving", "puerto morelos", "halocline", "reef", "local diving", "mexico"],
        "blocks": [
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>Sometimes the most magical dives are the ones closest to shore. Yesterday's shore dive at Ojo de Agua in Puerto Morelos reminded us why we fell in love with diving in the Riviera Maya. No boat needed—just a short swim from the beach to an underwater wonderland.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "The Magic of the Halocline", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>Ojo de Agua—Spanish for \"Eye of Water\"—gets its name from the freshwater springs that bubble up from the seafloor. Where this freshwater meets the saltwater of the Caribbean, something magical happens: a halocline forms, creating a shimmering, dancing layer that distorts light and makes you feel like you're diving through liquid glass.</p><p>The temperature difference is noticeable too. One moment you're in warm tropical water, the next you hit a cool pocket of fresh spring water. It's like nature's own thermocline surprise.</p>"
                },
            },
            {
                "type": "image_gallery",
                "data": {
                    "images": [
                        {"url": "https://nestorwheelock.com/media/library/2024/12/PC220010.jpg", "alt": "Halocline effect at Ojo de Agua"},
                        {"url": "https://nestorwheelock.com/media/library/2024/12/PC220027.jpg", "alt": "Coral formations at Puerto Morelos reef"},
                        {"url": "https://nestorwheelock.com/media/library/2024/12/PC220053.jpg", "alt": "Fish schooling over the reef"},
                        {"url": "https://nestorwheelock.com/media/library/2024/12/PC220076.jpg", "alt": "Underwater landscape Puerto Morelos"},
                    ],
                    "columns": 2,
                },
            },
            {
                "type": "heading",
                "data": {"text": "A Reef in Recovery", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>Like many Caribbean reefs, Ojo de Agua has faced challenges from coral bleaching events. But what we saw yesterday gave us hope. The reef is bouncing back. Juvenile corals are settling in, fish are recolonizing their territories, and the overall health of the ecosystem is improving.</p><p>This resilience is a testament to both nature's power to heal and the protection efforts of the Parque Nacional Arrecife de Puerto Morelos. When we take care of our reefs, they take care of us.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "Why We Love Shore Diving", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<ul><li><strong>Flexibility</strong> - Dive when conditions are right, not when the boat schedule says</li><li><strong>Longer bottom times</strong> - No rushing back to the boat</li><li><strong>Cost-effective</strong> - Perfect for multiple dives without the boat fees</li><li><strong>Intimate experience</strong> - Just you, your buddy, and the ocean</li></ul>"
                },
            },
            {
                "type": "image_gallery",
                "data": {
                    "images": [
                        {"url": "https://nestorwheelock.com/media/library/2024/12/PC220086.jpg", "alt": "Colorful reef life"},
                        {"url": "https://nestorwheelock.com/media/library/2024/12/PC220098.jpg", "alt": "Diver exploring Ojo de Agua"},
                        {"url": "https://nestorwheelock.com/media/library/2024/12/PC220115.jpg", "alt": "Marine life at Puerto Morelos"},
                        {"url": "https://nestorwheelock.com/media/library/2024/12/PC220137.jpg", "alt": "Sunset dive at Ojo de Agua"},
                    ],
                    "columns": 2,
                },
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>If you're visiting Playa del Carmen and want to experience something different from the typical boat dive, ask us about our Puerto Morelos shore diving excursions. Ojo de Agua is just one of the treasures waiting to be discovered.</p>"
                },
            },
        ],
    },
    {
        "slug": "hidden-treasures-mooring-systems",
        "title": "Hidden Treasures: The Secret Life of Mooring Systems",
        "category_slug": "marine-life",
        "excerpt": "Discover how underwater mooring systems transform from industrial infrastructure into thriving mini-ecosystems teeming with marine life.",
        "featured_image_url": "https://nestorwheelock.com/media/chat_uploads/2025/12/P8131448-sm.png",
        "reading_time_minutes": 5,
        "tags": ["marine life", "ecology", "infrastructure", "reef", "puerto morelos", "conservation"],
        "blocks": [
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>Most divers swim right past them—those heavy chains and concrete blocks anchoring navigation buoys in swimming areas. But if you slow down and look closely, you'll discover one of the ocean's best-kept secrets: mooring systems are underwater treasure troves of marine life.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "From Industrial to Ecological", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>These utilitarian structures weren't designed with marine life in mind. They exist to secure buoys, mark swimming areas, and protect boats from drifting. Yet give them a few years underwater, and something remarkable happens: they transform into thriving mini-reefs.</p><p>The concrete blocks become encrusted with sponges and corals. The chains develop a fuzzy coating of algae that attracts grazing fish. And the buoy itself creates a shaded refuge for juvenile fish seeking shelter from predators.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "Layers of Life", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>What fascinates us most is how different species partition these structures into distinct zones:</p><ul><li><strong>The Bottom Dwellers</strong> - Sea cucumbers, starfish, and crabs make homes around the anchor base</li><li><strong>The Chain Gang</strong> - Schooling fish congregate along the chain, using it as a reference point in the open water</li><li><strong>The Shade Seekers</strong> - Juvenile fish cluster near the surface in the buoy's shadow</li><li><strong>The Hunters</strong> - Barracuda and jacks patrol nearby, knowing prey concentrates here</li></ul>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "Stepping Stones Across the Sand", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>In areas where sandy bottom separates reef patches, mooring systems serve as crucial \"stepping stones\" for marine life. They provide habitat connectivity, allowing creatures to hop from one structure to another across otherwise barren stretches.</p><p>Next time you're diving in Puerto Morelos or anywhere with mooring systems, take a few minutes to hover by one and observe. You might be surprised by the diversity of life clinging to what most people consider just industrial equipment.</p>"
                },
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p><em>These observations come from countless dives inspecting moorings in the Parque Nacional Arrecife de Puerto Morelos—proof that wonder can be found in the most unexpected places.</em></p>"
                },
            },
        ],
    },
    {
        "slug": "15-misconceptions-scuba-certification",
        "title": "15 Common Misconceptions About Scuba Diving Certification",
        "category_slug": "training",
        "excerpt": "Think you know everything about getting certified? We debunk the most persistent myths about scuba training that might be holding you back.",
        "featured_image_url": "https://nestorwheelock.com/media/library/2025/12/P9142609-sm.png",
        "reading_time_minutes": 12,
        "tags": ["certification", "training", "padi", "myths", "beginners", "education"],
        "blocks": [
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>After years of teaching scuba diving, we've heard every misconception in the book. Some of these myths discourage potential divers from ever getting certified. Others create unnecessary anxiety during training. Let's set the record straight.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "Myth #1: Training is One-Size-Fits-All", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p><strong>Reality:</strong> Good instructors adapt their teaching to each student. While safety standards are non-negotiable, the way we explain concepts, demonstrate skills, and guide practice varies based on your learning style, comfort level, and pace. Diving education is structured, supportive, and human.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "Myth #2: You Need to Be Super Athletic", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p><strong>Reality:</strong> Diving is about buoyancy control and breathing technique, not brute strength. Some of our best students weren't athletes—they were patient people who mastered the art of moving efficiently underwater. Adaptive diving programs also prove that people with various physical abilities can become excellent divers.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "Myth #3: You Must Finish Training in One Trip", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p><strong>Reality:</strong> Referral programs let you start your certification at home (theory and pool work) and finish your open water dives on vacation. Life happens—training can pause for legitimate reasons, and skill refreshers can get you back on track.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "Myth #4: Pool Training Must Happen in a Pool", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p><strong>Reality:</strong> Confined water training can happen in pools, calm quarries, shallow beach areas, or any body of water meeting safety standards. What matters is controlled conditions, not the specific location.</p>"
                },
            },
            {
                "type": "image_gallery",
                "data": {
                    "images": [
                        {"url": "https://nestorwheelock.com/media/library/2025/12/P8242325-sm.png", "alt": "Student diver practicing skills"},
                        {"url": "https://nestorwheelock.com/media/library/2025/12/vlcsnap-2025-09-10-21h05m13s750.png", "alt": "Underwater training session"},
                    ],
                    "columns": 2,
                },
            },
            {
                "type": "heading",
                "data": {"text": "Myth #5: Certifications Are Only Valid Locally", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p><strong>Reality:</strong> PADI, SSI, and other major certification agencies are globally recognized. A certification earned in Mexico is valid in Thailand, Australia, the Maldives—anywhere in the world.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "Myth #6: You Need Lots of Dives Before Advanced Training", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p><strong>Reality:</strong> Advanced Open Water builds on your basic certification—you don't need 50 dives first. The course itself provides structured experience through specialty dives like deep diving and navigation. Training creates experience.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "Myth #7: There's Only One Way to Perform Skills", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p><strong>Reality:</strong> Multiple acceptable methods exist for most skills. Mask clearing, for example, can be done several ways—what matters is that water leaves your mask safely. Skill development is adaptation, not uniform repetition.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "Myth #8: Online Learning Expires Quickly", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p><strong>Reality:</strong> Digital learning materials typically offer extended or permanent access. You can (and should) revisit theory before trips. Diving knowledge isn't static—continuing education strengthens safety.</p>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "More Myths We Hear Regularly", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<ul><li><strong>\"Equipment setup is standardized\"</strong> - Various configurations exist based on diving goals and physical needs</li><li><strong>\"Kids can't use digital learning\"</strong> - Age-appropriate pathways exist with proper supervision</li><li><strong>\"Instructors must teach in a fixed order\"</strong> - Limited flexibility exists to arrange skills based on student comfort</li><li><strong>\"The only path is Open Water → Advanced → Rescue → Divemaster\"</strong> - Dozens of specialty courses offer different directions</li><li><strong>\"Becoming an instructor requires being young\"</strong> - Many become instructors later in life; judgment matters as much as water skills</li></ul>"
                },
            },
            {
                "type": "heading",
                "data": {"text": "The Bottom Line", "level": 2},
            },
            {
                "type": "rich_text",
                "data": {
                    "content": "<p>Modern scuba training balances standardized safety frameworks with individualized instruction. Don't let misconceptions hold you back from exploring the underwater world. The certification process is designed to be accessible, flexible, and—most importantly—to produce safe, confident divers.</p><p>Have questions about getting certified? <a href='/contact/'>Reach out to us</a>—we're happy to help you start your diving journey.</p>"
                },
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Seed blog categories and posts for Happy Diving"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Delete existing categories and posts and recreate",
        )

    def handle(self, *args, **options):
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(self.style.ERROR("No superuser found. Create one first."))
            return

        # Get or create author (Person)
        author = Person.objects.filter(deleted_at__isnull=True).first()
        if not author:
            self.stdout.write(
                self.style.WARNING("No Person found. Posts will be created without author.")
            )

        # Create categories
        self.stdout.write("\nCreating blog categories...")
        category_map = {}
        for cat_data in CATEGORIES:
            existing = BlogCategory.objects.filter(
                slug=cat_data["slug"], deleted_at__isnull=True
            ).first()
            if existing:
                if options["force"]:
                    existing.delete()
                    self.stdout.write(f"  Deleted existing category: {cat_data['name']}")
                else:
                    self.stdout.write(f"  Skipping existing category: {cat_data['name']}")
                    category_map[cat_data["slug"]] = existing
                    continue

            category = BlogCategory.objects.create(
                name=cat_data["name"],
                slug=cat_data["slug"],
                description=cat_data["description"],
                color=cat_data["color"],
                sort_order=cat_data["sort_order"],
            )
            category_map[cat_data["slug"]] = category
            self.stdout.write(self.style.SUCCESS(f"  Created: {cat_data['name']}"))

        # Create posts
        self.stdout.write("\nCreating blog posts...")
        for post_data in POSTS:
            existing = ContentPage.objects.filter(
                slug=post_data["slug"], deleted_at__isnull=True
            ).first()
            if existing:
                if options["force"]:
                    existing.delete()
                    self.stdout.write(f"  Deleted existing post: {post_data['title']}")
                else:
                    self.stdout.write(f"  Skipping existing post: {post_data['title']}")
                    continue

            category = category_map.get(post_data["category_slug"])

            post = ContentPage.objects.create(
                slug=post_data["slug"],
                title=post_data["title"],
                page_type=PageType.POST,
                status=PageStatus.DRAFT,
                access_level=AccessLevel.PUBLIC,
                author=author,
                excerpt=post_data["excerpt"],
                featured_image_url=post_data.get("featured_image_url", ""),
                reading_time_minutes=post_data.get("reading_time_minutes"),
                category=category,
                tags=post_data.get("tags", []),
                seo_title=post_data["title"][:70],
                seo_description=post_data["excerpt"][:160],
            )

            # Add content blocks
            for block_data in post_data["blocks"]:
                add_block(post, block_data["type"], block_data["data"])

            # Publish the post
            publish_page(post, admin_user)

            self.stdout.write(
                self.style.SUCCESS(f"  Created and published: {post_data['title']}")
            )

        self.stdout.write(self.style.SUCCESS("\nBlog seed complete!"))
        self.stdout.write(f"  Categories: {len(CATEGORIES)}")
        self.stdout.write(f"  Posts: {len(POSTS)}")
