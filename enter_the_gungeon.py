#!/usr/bin/env python3
"""
Enter the Gungeon - Complete Recreation
A top-down bullet hell roguelike shooter with pixel-perfect mechanics
"""

import pygame
import math
import random
import time
from enum import Enum

# Initialize Pygame
pygame.init()

# Game Constants
SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 900
GAME_WIDTH = 400
GAME_HEIGHT = 225
SCALE = 4

# Door Constants
DOOR_COLOR = (80, 60, 40)  # Wooden door color
DOOR_FRAME = (100, 100, 120)  # Door frame color

# Colors (Gungeon Palette)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
DARK_GRAY = (32, 32, 32)
GRAY = (64, 64, 64)
GUNMETAL = (42, 52, 57)
FLOOR = (48, 44, 36)
WALL = (28, 28, 28)
PLAYER_BLUE = (65, 105, 225)
ENEMY_RED = (220, 20, 60)
BULLET_YELLOW = (255, 255, 0)
BULLET_RED = (255, 69, 0)
HEALTH_RED = (220, 20, 60)
ARMOR_BLUE = (0, 100, 200)
GOLD = (255, 215, 0)
DOOR_COLOR = (139, 69, 19)
DOOR_FRAME = (101, 67, 33)
SPAWN_FLOOR = (64, 64, 96)
SPAWN_WALL = (48, 48, 72)

# Background colors and effects
DUNGEON_DARK = (20, 18, 15)
DUNGEON_ACCENT = (35, 30, 25)
STONE_LIGHT = (55, 50, 45)
STONE_DARK = (25, 22, 18)
MOSS_GREEN = (45, 65, 35)
TORCH_ORANGE = (255, 140, 0)
SHADOW_PURPLE = (25, 15, 35)
MYSTICAL_BLUE = (30, 50, 80)

class Vector2:
    def __init__(self, x=0.0, y=0.0):
        self.x = x
        self.y = y
    
    def __add__(self, other):
        return Vector2(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other):
        return Vector2(self.x - other.x, self.y - other.y)
    
    def __mul__(self, scalar):
        return Vector2(self.x * scalar, self.y * scalar)
    
    def normalize(self):
        length = math.sqrt(self.x**2 + self.y**2)
        if length > 0:
            return Vector2(self.x / length, self.y / length)
        return Vector2(0, 0)
    
    def distance_to(self, other):
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def angle_to(self, other):
        return math.atan2(other.y - self.y, other.x - self.x)

class Bullet:
    def __init__(self, x, y, angle, speed, damage, color=BULLET_YELLOW, size=4):
        self.pos = Vector2(x, y)
        self.velocity = Vector2(math.cos(angle) * speed, math.sin(angle) * speed)
        self.damage = damage
        self.color = color
        self.size = size
        self.lifetime = 5.0
        self.age = 0.0
        
    def update(self, dt):
        self.pos = self.pos + self.velocity * dt
        self.age += dt
        return self.age < self.lifetime
    
    def draw(self, screen, camera):
        screen_x = int(self.pos.x - camera.x)
        screen_y = int(self.pos.y - camera.y)
        pygame.draw.circle(screen, self.color, (screen_x, screen_y), self.size)

class Gun:
    def __init__(self, name, damage, fire_rate, bullet_speed, accuracy=1.0, ammo=-1, pellets=1):
        self.name = name
        self.damage = damage
        self.fire_rate = fire_rate
        self.bullet_speed = bullet_speed
        self.accuracy = accuracy
        self.ammo = ammo
        self.pellets = pellets  # Number of bullets fired per shot (for shotguns)
        self.fire_timer = 0.0
        
    def can_fire(self):
        return self.fire_timer <= 0 and (self.ammo > 0 or self.ammo == -1)
    
    def fire(self, x, y, angle):
        bullets = []
        if self.can_fire():
            self.fire_timer = 1.0 / self.fire_rate
            if self.ammo > 0:
                self.ammo -= 1
            
            # Fire multiple pellets for shotguns
            for i in range(self.pellets):
                if self.pellets > 1:
                    # Shotgun spread pattern
                    spread_angle = 0.4  # Total spread in radians
                    pellet_angle = angle + (i - (self.pellets - 1) / 2) * (spread_angle / (self.pellets - 1))
                else:
                    # Single bullet with accuracy spread
                    spread = (1.0 - self.accuracy) * 0.3
                    pellet_angle = angle + random.uniform(-spread, spread)
                
                bullet = Bullet(x, y, pellet_angle, self.bullet_speed, self.damage)
                bullets.append(bullet)
            
        return bullets
    
    def update(self, dt):
        self.fire_timer = max(0, self.fire_timer - dt)

class Player:
    def __init__(self, x, y):
        self.pos = Vector2(x, y)
        self.velocity = Vector2(0, 0)
        self.size = 8
        self.speed = 120
        self.health = 100
        self.max_health = 100
        self.armor = 0
        
        # Dodge mechanics
        self.dodge_speed = 250
        self.dodge_duration = 0.4
        self.dodge_cooldown = 1.0
        self.is_dodging = False
        self.dodge_timer = 0.0
        self.dodge_cooldown_timer = 0.0
        self.dodge_direction = Vector2(0, 0)
        self.invulnerable = False
        self.damage_flash_timer = 0.0
        
        # Weapons
        self.guns = [
            Gun("Rusty Sidearm", 8, 3, 200, 0.9, -1, 1),
            Gun("Shotgun", 12, 1.5, 180, 0.7, 50, 5),  # 5 pellets, lower damage per pellet
        ]
        self.current_gun = 0
        self.facing_angle = 0
        self.money = 0
        
    def update(self, dt, inputs, mouse_pos, camera):
        self.dodge_cooldown_timer = max(0, self.dodge_cooldown_timer - dt)
        self.damage_flash_timer = max(0, self.damage_flash_timer - dt)
        
        # End invulnerability after damage flash
        if self.damage_flash_timer <= 0 and self.invulnerable and not self.is_dodging:
            self.invulnerable = False
        
        if self.is_dodging:
            self.dodge_timer += dt
            if self.dodge_timer >= self.dodge_duration:
                self.is_dodging = False
                self.invulnerable = False
                self.dodge_timer = 0
            else:
                progress = self.dodge_timer / self.dodge_duration
                ease_factor = 1.0 - (progress * progress)
                self.velocity = self.dodge_direction * self.dodge_speed * ease_factor
        else:
            move_dir = Vector2(0, 0)
            if inputs.get('left', False):
                move_dir.x -= 1
            if inputs.get('right', False):
                move_dir.x += 1
            if inputs.get('up', False):
                move_dir.y -= 1
            if inputs.get('down', False):
                move_dir.y += 1
            
            if move_dir.x != 0 or move_dir.y != 0:
                move_dir = move_dir.normalize()
            self.velocity = move_dir * self.speed
            
            world_mouse_x = mouse_pos[0] + camera.x
            world_mouse_y = mouse_pos[1] + camera.y
            self.facing_angle = math.atan2(world_mouse_y - self.pos.y, world_mouse_x - self.pos.x)
        
        self.pos = self.pos + self.velocity * dt
        
        for gun in self.guns:
            gun.update(dt)
    
    def dodge_roll(self):
        if not self.is_dodging and self.dodge_cooldown_timer <= 0:
            self.is_dodging = True
            self.invulnerable = True
            self.dodge_timer = 0
            self.dodge_cooldown_timer = self.dodge_cooldown
            
            if self.velocity.x != 0 or self.velocity.y != 0:
                self.dodge_direction = self.velocity.normalize()
            else:
                self.dodge_direction = Vector2(math.cos(self.facing_angle), math.sin(self.facing_angle))
    
    def fire_weapon(self):
        gun = self.guns[self.current_gun]
        return gun.fire(self.pos.x, self.pos.y, self.facing_angle)
    
    def switch_weapon(self):
        self.current_gun = (self.current_gun + 1) % len(self.guns)
    
    def take_damage(self, amount):
        if not self.invulnerable:
            if self.armor > 0:
                self.armor -= 1
            else:
                self.health = max(0, self.health - amount)
            
            # Add brief invulnerability after taking damage - increased duration
            self.invulnerable = True
            self.damage_flash_timer = 0.6  # Increased from 0.3 for better protection
            
            # Screen shake effect would go here if implemented
            return True
        return False
    
    def draw(self, screen, camera):
        screen_x = int(self.pos.x - camera.x)
        screen_y = int(self.pos.y - camera.y)
        
        # Create a pixel-art style character (anthropomorphic animal like in the image)
        base_color = (139, 69, 19)  # Brown
        shirt_color = (178, 34, 34)  # Red shirt
        
        if self.invulnerable and int(time.time() * 20) % 2:
            base_color = WHITE
            shirt_color = (255, 200, 200)
        
        # Body (main rectangle)
        body_rect = (screen_x - 6, screen_y - 4, 12, 8)
        pygame.draw.rect(screen, shirt_color, body_rect)
        pygame.draw.rect(screen, (50, 50, 50), body_rect, 1)  # Dark outline
        
        # Head (circle above body)
        head_center = (screen_x, screen_y - 6)
        pygame.draw.circle(screen, base_color, head_center, 4)
        pygame.draw.circle(screen, (50, 50, 50), head_center, 4, 1)  # Dark outline
        
        # Ears (small triangles)
        ear1_points = [(screen_x - 3, screen_y - 9), (screen_x - 1, screen_y - 11), (screen_x - 5, screen_y - 11)]
        ear2_points = [(screen_x + 3, screen_y - 9), (screen_x + 1, screen_y - 11), (screen_x + 5, screen_y - 11)]
        pygame.draw.polygon(screen, base_color, ear1_points)
        pygame.draw.polygon(screen, base_color, ear2_points)
        pygame.draw.polygon(screen, (50, 50, 50), ear1_points, 1)
        pygame.draw.polygon(screen, (50, 50, 50), ear2_points, 1)
        
        # Eyes (small white dots)
        pygame.draw.circle(screen, WHITE, (screen_x - 2, screen_y - 6), 1)
        pygame.draw.circle(screen, WHITE, (screen_x + 2, screen_y - 6), 1)
        
        # Arms
        arm_length = 4
        arm_angle = self.facing_angle
        arm_end_x = screen_x + math.cos(arm_angle) * arm_length
        arm_end_y = screen_y + math.sin(arm_angle) * arm_length
        pygame.draw.line(screen, base_color, (screen_x - 3, screen_y - 1), (arm_end_x - 3, arm_end_y), 2)
        pygame.draw.line(screen, base_color, (screen_x + 3, screen_y - 1), (arm_end_x + 3, arm_end_y), 2)
        
        # Legs
        pygame.draw.rect(screen, base_color, (screen_x - 3, screen_y + 2, 2, 4))
        pygame.draw.rect(screen, base_color, (screen_x + 1, screen_y + 2, 2, 4))
        pygame.draw.rect(screen, (50, 50, 50), (screen_x - 3, screen_y + 2, 2, 4), 1)
        pygame.draw.rect(screen, (50, 50, 50), (screen_x + 1, screen_y + 2, 2, 4), 1)
        
        # Weapon/gun
        gun_end_x = screen_x + math.cos(self.facing_angle) * 12
        gun_end_y = screen_y + math.sin(self.facing_angle) * 12
        pygame.draw.line(screen, (64, 64, 64), (arm_end_x, arm_end_y), (gun_end_x, gun_end_y), 3)
        pygame.draw.circle(screen, (128, 128, 128), (gun_end_x, gun_end_y), 2)
        
        # Muzzle flash if firing
        current_gun = self.guns[self.current_gun]
        if current_gun.fire_timer > (1.0 / current_gun.fire_rate) - 0.1:
            flash_points = []
            for i in range(6):
                angle = self.facing_angle + (i - 2.5) * 0.3
                flash_x = gun_end_x + math.cos(angle) * 6
                flash_y = gun_end_y + math.sin(angle) * 6
                flash_points.append((flash_x, flash_y))
            if len(flash_points) > 2:
                pygame.draw.polygon(screen, BULLET_YELLOW, flash_points)

class Enemy:
    def __init__(self, x, y, enemy_type="basic", level=1):
        self.pos = Vector2(x, y)
        self.velocity = Vector2(0, 0)
        self.size = 8
        self.health = 30
        self.max_health = 30
        self.speed = 60
        self.fire_timer = 0.0
        self.fire_rate = 0.5  # Much slower firing
        self.detection_range = 180
        self.damage = 8  # Increased from 3
        self.contact_damage = 12  # Increased from 5
        self.contact_damage_cooldown = 2.0  # Longer cooldown
        self.last_contact_damage = 0.0
        
        # AI behavior variables
        self.enemy_type = enemy_type
        self.state = "patrol"  # patrol, chase, circle, retreat
        self.state_timer = 0.0
        self.patrol_target = Vector2(x + random.randint(-50, 50), y + random.randint(-50, 50))
        self.circle_angle = 0.0
        self.circle_radius = 80
        self.retreat_timer = 0.0
        self.sight_blocked = False
        
        # Different enemy types - much more balanced
        if enemy_type == "aggressive":
            self.speed = 80
            self.fire_rate = 0.8  # Slower than before
            self.contact_damage = 18  # Increased from 8
            self.damage = 10  # Increased from 4
        elif enemy_type == "sniper":
            self.speed = 40
            self.fire_rate = 0.3  # Much slower
            self.detection_range = 250
            self.damage = 15  # Increased from 6
        elif enemy_type == "rusher":
            self.speed = 100
            self.fire_rate = 0.2  # Barely shoots
            self.contact_damage = 20  # Increased from 10
            self.size = 6
            self.damage = 6  # Increased from 2
        
        # Level-specific adjustments - scale stats with level
        level_multiplier = 1 + 0.15 * (level - 1)  # 15% increase per level
        self.health = max(1, int(self.health * level_multiplier))
        self.max_health = self.health
        self.damage = max(1, int(self.damage * level_multiplier))
        self.contact_damage = max(1, int(self.contact_damage * level_multiplier))
        
        # Slightly increase detection range and speed at higher levels
        if level > 3:
            self.detection_range = int(self.detection_range * (1 + 0.1 * (level - 3)))
            self.speed = int(self.speed * (1 + 0.05 * (level - 3)))
    
    def update(self, dt, player_pos, walls):
        self.state_timer += dt
        self.last_contact_damage += dt
        distance_to_player = self.pos.distance_to(player_pos)
        
        # State management
        if distance_to_player < self.detection_range:
            self.update_ai_behavior(dt, player_pos, walls, distance_to_player)
        else:
            self.patrol_behavior(dt)
            
        self.pos = self.pos + self.velocity * dt
        self.fire_timer += dt
    
    def update_ai_behavior(self, dt, player_pos, walls, distance_to_player):
        # Check line of sight
        self.sight_blocked = self.check_line_of_sight(player_pos, walls)
        
        if self.enemy_type == "rusher":
            self.rusher_behavior(player_pos, distance_to_player)
        elif self.enemy_type == "sniper":
            self.sniper_behavior(player_pos, distance_to_player)
        else:
            self.smart_chase_behavior(player_pos, distance_to_player)
    
    def rusher_behavior(self, player_pos, distance):
        if distance > 30:
            # Charge directly at player
            direction = (player_pos - self.pos).normalize()
            self.velocity = direction * self.speed
        else:
            # Circle around player when close
            self.circle_angle += 0.05
            circle_pos = player_pos + Vector2(
                math.cos(self.circle_angle) * 25,
                math.sin(self.circle_angle) * 25
            )
            direction = (circle_pos - self.pos).normalize()
            self.velocity = direction * self.speed * 0.7
    
    def sniper_behavior(self, player_pos, distance):
        if distance > 120:
            # Move to optimal range
            direction = (player_pos - self.pos).normalize()
            self.velocity = direction * self.speed * 0.6
        elif distance < 80:
            # Retreat to maintain distance
            direction = (self.pos - player_pos).normalize()
            self.velocity = direction * self.speed * 0.8
        else:
            # Stay in position and strafe
            perpendicular = Vector2(-self.velocity.y, self.velocity.x).normalize()
            if self.state_timer > 2.0:
                self.state_timer = 0
                perpendicular = perpendicular * -1
            self.velocity = perpendicular * self.speed * 0.4
    
    def smart_chase_behavior(self, player_pos, distance):
        if self.sight_blocked:
            # Try to find path around obstacles
            self.navigate_around_obstacles(player_pos)
        else:
            if distance > 100:
                # Chase behavior with slight prediction
                predicted_pos = player_pos + Vector2(random.randint(-20, 20), random.randint(-20, 20))
                direction = (predicted_pos - self.pos).normalize()
                self.velocity = direction * self.speed
            elif distance > 50:
                # Circle strafe
                angle_to_player = self.pos.angle_to(player_pos)
                circle_angle = angle_to_player + math.pi/2 + math.sin(self.state_timer * 2) * 0.5
                direction = Vector2(math.cos(circle_angle), math.sin(circle_angle))
                self.velocity = direction * self.speed * 0.7
            else:
                # Retreat slightly
                direction = (self.pos - player_pos).normalize()
                self.velocity = direction * self.speed * 0.5
    
    def navigate_around_obstacles(self, player_pos):
        # Simple obstacle avoidance
        direction_to_player = (player_pos - self.pos).normalize()
        left_direction = Vector2(-direction_to_player.y, direction_to_player.x)
        right_direction = Vector2(direction_to_player.y, -direction_to_player.x)
        
        # Randomly choose left or right
        if random.random() < 0.5:
            self.velocity = left_direction * self.speed * 0.6
        else:
            self.velocity = right_direction * self.speed * 0.6
    
    def patrol_behavior(self, dt):
        # Simple patrol when player not detected
        direction = (self.patrol_target - self.pos)
        if direction.distance_to(Vector2(0, 0)) < 20:
            # Choose new patrol target
            self.patrol_target = self.pos + Vector2(
                random.randint(-100, 100),
                random.randint(-100, 100)
            )
        else:
            self.velocity = direction.normalize() * self.speed * 0.3
    
    def check_line_of_sight(self, player_pos, walls):
        # Simple line of sight check
        direction = (player_pos - self.pos)
        distance = direction.distance_to(Vector2(0, 0))
        if distance == 0 or distance < 8:
            return False
            
        steps = int(distance / 8)
        if steps == 0:
            return False
            
        step_vec = direction * (1.0 / steps)
        
        current_pos = Vector2(self.pos.x, self.pos.y)
        for _ in range(steps):
            current_pos = current_pos + step_vec
            tile_x = int(current_pos.x // 16)
            tile_y = int(current_pos.y // 16)
            if (tile_x, tile_y) in walls:
                return True
        return False
    
    def can_fire(self):
        return self.fire_timer >= 1.0 / self.fire_rate and not self.sight_blocked
    
    def fire_at_player(self, player_pos):
        if self.can_fire():
            angle = self.pos.angle_to(player_pos)
            self.fire_timer = 0
            
            # Different firing patterns for different enemy types
            if self.enemy_type == "sniper":
                return [Bullet(self.pos.x, self.pos.y, angle, 200, self.damage, BULLET_RED, 3)]
            elif self.enemy_type == "aggressive":
                # Single bullet instead of burst - much easier
                return [Bullet(self.pos.x, self.pos.y, angle, 160, self.damage, BULLET_RED, 3)]
            else:
                return [Bullet(self.pos.x, self.pos.y, angle, 150, self.damage, BULLET_RED, 3)]
        return []
    
    def can_contact_damage(self):
        return self.last_contact_damage >= self.contact_damage_cooldown
    
    def deal_contact_damage(self):
        if self.can_contact_damage():
            self.last_contact_damage = 0.0
            return self.contact_damage
        return 0
    
    def take_damage(self, amount):
        self.health = max(0, self.health - amount)
        return self.health <= 0
    
    def draw(self, screen, camera):
        screen_x = int(self.pos.x - camera.x)
        screen_y = int(self.pos.y - camera.y)
        
        # Base colors for different enemy types (yellow/orange theme like in image)
        base_colors = {
            "basic": (255, 165, 0),      # Orange
            "aggressive": (255, 140, 0),  # Dark orange  
            "sniper": (218, 165, 32),     # Golden rod
            "rusher": (255, 69, 0)        # Red orange
        }
        
        base_color = base_colors.get(self.enemy_type, (255, 165, 0))
        body_color = (200, 120, 0)  # Darker orange for body
        
        # Body (main part)
        body_width = self.size + 2
        body_height = self.size
        pygame.draw.rect(screen, body_color, (screen_x - body_width//2, screen_y - body_height//2, body_width, body_height))
        pygame.draw.rect(screen, (50, 50, 50), (screen_x - body_width//2, screen_y - body_height//2, body_width, body_height), 1)
        
        # Head (circle above body)
        head_y = screen_y - self.size//2 - 3
        pygame.draw.circle(screen, base_color, (screen_x, head_y), 4)
        pygame.draw.circle(screen, (50, 50, 50), (screen_x, head_y), 4, 1)
        
        # Eyes (small black dots)
        pygame.draw.circle(screen, BLACK, (screen_x - 2, head_y), 1)
        pygame.draw.circle(screen, BLACK, (screen_x + 2, head_y), 1)
        
        # Simple legs
        leg_color = (150, 90, 0)
        pygame.draw.rect(screen, leg_color, (screen_x - 2, screen_y + self.size//2, 1, 3))
        pygame.draw.rect(screen, leg_color, (screen_x + 1, screen_y + self.size//2, 1, 3))
        
        # Type-specific details
        if self.enemy_type == "sniper":
            # Rifle
            rifle_end_x = screen_x + 8
            rifle_end_y = screen_y
            pygame.draw.line(screen, (64, 64, 64), (screen_x + 3, screen_y), (rifle_end_x, rifle_end_y), 2)
            pygame.draw.circle(screen, (128, 128, 128), (rifle_end_x, rifle_end_y), 1)
            
        elif self.enemy_type == "rusher":
            # Spikes or claws
            spike_points = [
                (screen_x - 3, screen_y - 1),
                (screen_x - 5, screen_y - 3),
                (screen_x - 1, screen_y - 3)
            ]
            pygame.draw.polygon(screen, (180, 180, 180), spike_points)
            
            spike_points2 = [
                (screen_x + 3, screen_y - 1),
                (screen_x + 5, screen_y - 3),
                (screen_x + 1, screen_y - 3)
            ]
            pygame.draw.polygon(screen, (180, 180, 180), spike_points2)
            
        elif self.enemy_type == "aggressive":
            # Double guns
            gun1_end_x = screen_x + 6
            gun1_end_y = screen_y - 1
            gun2_end_x = screen_x + 6
            gun2_end_y = screen_y + 1
            pygame.draw.line(screen, (64, 64, 64), (screen_x + 2, screen_y - 1), (gun1_end_x, gun1_end_y), 1)
            pygame.draw.line(screen, (64, 64, 64), (screen_x + 2, screen_y + 1), (gun2_end_x, gun2_end_y), 1)
        
        else:  # basic
            # Simple gun
            gun_end_x = screen_x + 6
            gun_end_y = screen_y
            pygame.draw.line(screen, (64, 64, 64), (screen_x + 2, screen_y), (gun_end_x, gun_end_y), 2)
        
        # Health bar
        if self.health < self.max_health:
            bar_width = 16
            bar_height = 3
            health_ratio = self.health / self.max_health
            
            pygame.draw.rect(screen, DARK_GRAY, (screen_x - bar_width//2, screen_y - self.size//2 - 12, bar_width, bar_height))
            pygame.draw.rect(screen, HEALTH_RED, (screen_x - bar_width//2, screen_y - self.size//2 - 12, int(bar_width * health_ratio), bar_height))

class Room:
    def __init__(self, width=25, height=20, level=1):
        self.width = width
        self.height = height
        self.level = level
        self.enemies = []
        self.player_bullets = []
        self.enemy_bullets = []
        self.cleared = False
        self.walls = set()
        self.floor_tiles = set()
        
        self.generate_room()
        
    def generate_room(self):
        # Create floor
        for x in range(1, self.width - 1):
            for y in range(1, self.height - 1):
                self.floor_tiles.add((x, y))
        
        # Create walls around perimeter
        for x in range(self.width):
            self.walls.add((x, 0))
            self.walls.add((x, self.height - 1))
        for y in range(self.height):
            self.walls.add((0, y))
            self.walls.add((self.width - 1, y))
        
        # Add obstacles - more obstacles on higher levels
        base_obstacles = 3
        level_obstacles = min(self.level * 2, 12)  # Cap at 12 obstacles
        num_obstacles = random.randint(base_obstacles, base_obstacles + level_obstacles)
        
        for _ in range(num_obstacles):
            x = random.randint(2, self.width - 3)
            y = random.randint(2, self.height - 3)
            
            for dx in range(2):
                for dy in range(2):
                    if random.random() < 0.7:
                        wall_x, wall_y = x + dx, y + dy
                        if (wall_x, wall_y) in self.floor_tiles:
                            self.walls.add((wall_x, wall_y))
                            self.floor_tiles.remove((wall_x, wall_y))
        
        self.spawn_enemies()
        
    def spawn_enemies(self):
        # Scale enemy count with level - much more enemies now
        base_enemies = 5  # Increased from 2
        level_bonus = min(self.level - 1, 12)  # Up to 12 extra enemies
        min_enemies = base_enemies + level_bonus // 2
        max_enemies = base_enemies + level_bonus + 3  # Even more max enemies
        num_enemies = random.randint(min_enemies, max_enemies)
        
        enemy_types = ["basic", "aggressive", "sniper", "rusher"]
        
        # Adjust enemy type weights based on level
        if self.level <= 2:
            weights = [70, 15, 10, 5]  # Mostly basic enemies early on
        elif self.level <= 4:
            weights = [50, 25, 15, 10]  # More variety
        elif self.level <= 6:
            weights = [35, 30, 20, 15]  # Balanced mix
        elif self.level <= 8:
            weights = [25, 30, 25, 20]  # More dangerous enemies
        else:
            weights = [15, 35, 25, 25]  # Mostly dangerous enemies at high levels
        
        for _ in range(num_enemies):
            attempts = 0
            while attempts < 100:  # More attempts to place enemies
                x = random.randint(3, self.width - 4) * 16
                y = random.randint(3, self.height - 4) * 16
                
                tile_x, tile_y = x // 16, y // 16
                if (tile_x, tile_y) in self.floor_tiles:
                    # Make sure enemies don't spawn too close to each other
                    too_close = False
                    for existing_enemy in self.enemies:
                        if Vector2(x, y).distance_to(existing_enemy.pos) < 32:
                            too_close = True
                            break
                    
                    if not too_close:
                        # Choose enemy type based on level-adjusted weights
                        enemy_type = random.choices(enemy_types, weights=weights)[0]
                        self.enemies.append(Enemy(x, y, enemy_type, self.level))
                        break
                attempts += 1
    
    def update(self, dt, player):
        for enemy in self.enemies[:]:
            enemy.update(dt, player.pos, self.walls)
            bullets = enemy.fire_at_player(player.pos)
            if bullets:
                for bullet in bullets:
                    self.enemy_bullets.append(bullet)
            
            # Handle boss special attacks
            if hasattr(enemy, 'special_attack'):
                special_bullets = enemy.update(dt, player.pos, self.walls)
                if special_bullets:
                    for bullet in special_bullets:
                        self.enemy_bullets.append(bullet)
        
        # Enemy separation - prevent clustering
        for i, enemy1 in enumerate(self.enemies):
            for j, enemy2 in enumerate(self.enemies[i+1:], i+1):
                distance = enemy1.pos.distance_to(enemy2.pos)
                min_distance = (enemy1.size + enemy2.size) / 2.0 + 5  # Small buffer
                
                if distance < min_distance and distance > 0.1:
                    # Push enemies apart
                    push_direction = (enemy1.pos - enemy2.pos).normalize()
                    push_strength = (min_distance - distance) * 0.5
                    
                    enemy1.pos = enemy1.pos + push_direction * push_strength * 0.5
                    enemy2.pos = enemy2.pos - push_direction * push_strength * 0.5
                    
                    # Validate positions
                    self.validate_enemy_position(enemy1)
                    self.validate_enemy_position(enemy2)
        
        self.player_bullets = [b for b in self.player_bullets if b.update(dt)]
        self.enemy_bullets = [b for b in self.enemy_bullets if b.update(dt)]
        
        if not self.cleared and len(self.enemies) == 0:
            self.cleared = True
    
    def check_collisions(self, player, game_instance=None):
        # Player bullets vs enemies
        for bullet in self.player_bullets[:]:
            for enemy in self.enemies[:]:
                if bullet.pos.distance_to(enemy.pos) < enemy.size + bullet.size:
                    if enemy.take_damage(bullet.damage):
                        self.enemies.remove(enemy)
                        player.money += random.randint(2, 8)  # More money reward
                        if game_instance:
                            game_instance.enemies_killed += 1
                    if bullet in self.player_bullets:
                        self.player_bullets.remove(bullet)
                    break
        
        # Enemy bullets vs player
        for bullet in self.enemy_bullets[:]:
            if bullet.pos.distance_to(player.pos) < player.size + bullet.size:
                player.take_damage(bullet.damage)
                self.enemy_bullets.remove(bullet)
        
        # Player vs enemies (contact damage) - only check if player is not invulnerable
        if not player.invulnerable:
            for enemy in self.enemies[:]:
                distance = enemy.pos.distance_to(player.pos)
                # Fixed collision threshold - proper circle-to-circle collision
                collision_threshold = (enemy.size + player.size) / 2.0
                
                if distance < collision_threshold and distance > 0.1:  # Avoid division by zero
                    contact_damage = enemy.deal_contact_damage()
                    if contact_damage > 0:
                        # Calculate knockback direction before taking damage
                        push_direction = (player.pos - enemy.pos).normalize()
                        
                        # Take damage (this will set invulnerability)
                        player.take_damage(contact_damage)
                        
                        # Apply knockback to separate player and enemy
                        knockback_strength = 25
                        player.pos = player.pos + push_direction * knockback_strength
                        
                        # Push enemy back slightly to prevent sticking
                        enemy.pos = enemy.pos - push_direction * 8
                        
                        # Ensure entities don't get pushed into walls
                        self.validate_position(player.pos, player.size)
                        self.validate_enemy_position(enemy)
        
        # Bullets vs walls
        for bullet in self.player_bullets[:]:
            tile_x = int(bullet.pos.x // 16)
            tile_y = int(bullet.pos.y // 16)
            if (tile_x, tile_y) in self.walls:
                self.player_bullets.remove(bullet)
        
        for bullet in self.enemy_bullets[:]:
            tile_x = int(bullet.pos.x // 16)
            tile_y = int(bullet.pos.y // 16)
            if (tile_x, tile_y) in self.walls:
                self.enemy_bullets.remove(bullet)
    
    def add_player_bullet(self, bullets):
        if bullets:
            if isinstance(bullets, list):
                self.player_bullets.extend(bullets)
            else:
                self.player_bullets.append(bullets)
    
    def draw(self, screen, camera):
        # Draw floor with subtle overlay on background
        for x, y in self.floor_tiles:
            screen_x = x * 16 - camera.x
            screen_y = y * 16 - camera.y
            # Create a subtle floor overlay that blends with background
            floor_surface = pygame.Surface((16, 16))
            floor_surface.set_alpha(120)  # Semi-transparent
            floor_surface.fill((FLOOR[0] + 10, FLOOR[1] + 10, FLOOR[2] + 10))
            screen.blit(floor_surface, (screen_x, screen_y))
        
        # Draw walls with enhanced depth
        for x, y in self.walls:
            screen_x = x * 16 - camera.x
            screen_y = y * 16 - camera.y
            # Main wall
            pygame.draw.rect(screen, WALL, (screen_x, screen_y, 16, 16))
            # Enhanced border with depth
            pygame.draw.rect(screen, (WALL[0] - 10, WALL[1] - 10, WALL[2] - 10), (screen_x, screen_y, 16, 16), 2)
            # Inner highlight for depth
            pygame.draw.rect(screen, (WALL[0] + 15, WALL[1] + 15, WALL[2] + 15), (screen_x + 2, screen_y + 2, 12, 12), 1)
        
        # Draw entities
        for enemy in self.enemies:
            enemy.draw(screen, camera)
        
        for bullet in self.player_bullets:
            bullet.draw(screen, camera)
        
        for bullet in self.enemy_bullets:
            bullet.draw(screen, camera)
    
    def validate_position(self, pos, size):
        """Ensure position is not inside walls"""
        margin = size / 2 + 2  # Extra safety margin
        
        # Check boundaries first
        room_width = self.width * 16
        room_height = self.height * 16
        
        if pos.x < margin:
            pos.x = margin
        elif pos.x > room_width - margin:
            pos.x = room_width - margin
            
        if pos.y < margin:
            pos.y = margin
        elif pos.y > room_height - margin:
            pos.y = room_height - margin
        
        # Check wall collisions and push away
        tile_x = int(pos.x // 16)
        tile_y = int(pos.y // 16)
        
        # Check surrounding tiles in a 3x3 grid
        push_x = 0
        push_y = 0
        collision_count = 0
        
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                check_x = tile_x + dx
                check_y = tile_y + dy
                if (check_x, check_y) in self.walls:
                    wall_center_x = check_x * 16 + 8
                    wall_center_y = check_y * 16 + 8
                    wall_distance = Vector2(wall_center_x, wall_center_y).distance_to(pos)
                    
                    required_distance = size / 2 + 8  # Wall half-size + entity half-size
                    
                    if wall_distance < required_distance:  # Wall collision
                        collision_count += 1
                        # Calculate push direction
                        if wall_distance > 0.1:
                            push_dir = (pos - Vector2(wall_center_x, wall_center_y)).normalize()
                            push_strength = required_distance - wall_distance + 1  # Extra margin
                            push_x += push_dir.x * push_strength
                            push_y += push_dir.y * push_strength
        
        # Apply accumulated push
        if collision_count > 0:
            pos.x += push_x / collision_count
            pos.y += push_y / collision_count
            
            # Ensure we're still within room bounds after push
            if pos.x < margin:
                pos.x = margin
            elif pos.x > room_width - margin:
                pos.x = room_width - margin
                
            if pos.y < margin:
                pos.y = margin
            elif pos.y > room_height - margin:
                pos.y = room_height - margin
    
    def validate_enemy_position(self, enemy):
        """Ensure enemy position is valid"""
        self.validate_position(enemy.pos, enemy.size)

class Camera:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.target_x = 0
        self.target_y = 0
        self.smoothing = 0.15
    
    def follow(self, target_x, target_y):
        self.target_x = target_x - GAME_WIDTH // 2
        self.target_y = target_y - GAME_HEIGHT // 2
    
    def update(self, dt):
        self.x += (self.target_x - self.x) * self.smoothing
        self.y += (self.target_y - self.y) * self.smoothing

class Door:
    def __init__(self, x, y, direction="horizontal"):
        self.x = x
        self.y = y
        self.pos = Vector2(x, y)  # Add position vector for distance calculations
        self.direction = direction  # "horizontal" or "vertical"
        self.is_open = False
        self.open_progress = 0.0
        self.open_speed = 3.0
        self.width = 32 if direction == "horizontal" else 16
        self.height = 16 if direction == "horizontal" else 32
        
    def update(self, dt, player_nearby=False):
        target_progress = 1.0 if player_nearby else 0.0
        
        if self.open_progress < target_progress:
            self.open_progress = min(1.0, self.open_progress + self.open_speed * dt)
        elif self.open_progress > target_progress:
            self.open_progress = max(0.0, self.open_progress - self.open_speed * dt)
            
        self.is_open = self.open_progress > 0.5
    
    def can_pass_through(self):
        return self.is_open
    
    def get_collision_rect(self):
        if self.is_open:
            return None
        return (self.x, self.y, self.width, self.height)
    
    def draw(self, screen, camera):
        screen_x = int(self.x - camera.x)
        screen_y = int(self.y - camera.y)
        
        # Enhanced door frame with better visibility
        frame_rect = (screen_x - 3, screen_y - 3, self.width + 6, self.height + 6)
        pygame.draw.rect(screen, (100, 100, 120), frame_rect)  # Brighter frame
        pygame.draw.rect(screen, (150, 150, 170), frame_rect, 2)  # Brighter border
        
        if self.direction == "horizontal":
            # Enhanced horizontal sliding door
            door_width = int(self.width * (1.0 - self.open_progress))
            left_door_width = door_width // 2
            right_door_width = door_width - left_door_width
            
            # Left door panel with enhanced visuals
            if left_door_width > 0:
                left_rect = (screen_x, screen_y, left_door_width, self.height)
                pygame.draw.rect(screen, (80, 60, 40), left_rect)  # Darker wood color
                pygame.draw.rect(screen, (120, 100, 60), left_rect, 2)  # Brighter border
                # Door handle
                handle_x = screen_x + left_door_width - 4
                handle_y = screen_y + self.height // 2 - 2
                pygame.draw.circle(screen, (200, 200, 200), (handle_x, handle_y), 2)
            
            # Right door panel with enhanced visuals
            if right_door_width > 0:
                right_rect = (screen_x + self.width - right_door_width, screen_y, right_door_width, self.height)
                pygame.draw.rect(screen, (80, 60, 40), right_rect)  # Darker wood color
                pygame.draw.rect(screen, (120, 100, 60), right_rect, 2)  # Brighter border
                # Door handle
                handle_x = screen_x + self.width - right_door_width + 4
                handle_y = screen_y + self.height // 2 - 2
                pygame.draw.circle(screen, (200, 200, 200), (handle_x, handle_y), 2)
        else:
            # Enhanced vertical sliding door
            door_height = int(self.height * (1.0 - self.open_progress))
            top_door_height = door_height // 2
            bottom_door_height = door_height - top_door_height
            
            # Top door panel with enhanced visuals
            if top_door_height > 0:
                top_rect = (screen_x, screen_y, self.width, top_door_height)
                pygame.draw.rect(screen, (80, 60, 40), top_rect)  # Darker wood color
                pygame.draw.rect(screen, (120, 100, 60), top_rect, 2)  # Brighter border
                # Door handle
                handle_x = screen_x + self.width // 2 - 2
                handle_y = screen_y + top_door_height - 4
                pygame.draw.circle(screen, (200, 200, 200), (handle_x, handle_y), 2)
            
            # Bottom door panel with enhanced visuals
            if bottom_door_height > 0:
                bottom_rect = (screen_x, screen_y + self.height - bottom_door_height, self.width, bottom_door_height)
                pygame.draw.rect(screen, (80, 60, 40), bottom_rect)  # Darker wood color
                pygame.draw.rect(screen, (120, 100, 60), bottom_rect, 2)  # Brighter border
                # Door handle
                handle_x = screen_x + self.width // 2 - 2
                handle_y = screen_y + self.height - bottom_door_height + 4
                pygame.draw.circle(screen, (200, 200, 200), (handle_x, handle_y), 2)
        
        # Add sliding door effect indicator when opening/closing
        if 0.1 < self.open_progress < 0.9:
            # Draw sliding effect lines
            effect_color = (150, 200, 255)
            if self.direction == "horizontal":
                for i in range(3):
                    y_offset = screen_y + 4 + i * 4
                    pygame.draw.line(screen, effect_color, 
                                   (screen_x + 4, y_offset), 
                                   (screen_x + self.width - 4, y_offset), 1)
            else:
                for i in range(3):
                    x_offset = screen_x + 4 + i * 4
                    pygame.draw.line(screen, effect_color, 
                                   (x_offset, screen_y + 4), 
                                   (x_offset, screen_y + self.height - 4), 1)

class Shop:
    def __init__(self):
        self.items = [
            {"name": "Health Medkit", "price": 25, "description": "Restore 30 HP", "type": "health", "value": 30},
            {"name": "Armor Vest", "price": 40, "description": "Gain 1 Armor", "type": "armor", "value": 1},
            {"name": "Damage Boost", "price": 60, "description": "Increase weapon damage by 25%", "type": "damage", "value": 1.25},
            {"name": "Speed Boost", "price": 35, "description": "Increase movement speed by 20%", "type": "speed", "value": 1.2},
            {"name": "Max Health Up", "price": 80, "description": "Increase max health by 20", "type": "max_health", "value": 20},
            {"name": "Ammo Pack", "price": 15, "description": "Refill shotgun ammo", "type": "ammo", "value": 50}
        ]
        self.is_open = False
        self.selected_item = 0
        
    def toggle(self):
        self.is_open = not self.is_open
        
    def buy_item(self, player, item_index):
        if item_index < len(self.items):
            item = self.items[item_index]
            if player.money >= item["price"]:
                player.money -= item["price"]
                self.apply_item_effect(player, item)
                return True
        return False
    
    def apply_item_effect(self, player, item):
        if item["type"] == "health":
            player.health = min(player.max_health, player.health + item["value"])
        elif item["type"] == "armor":
            player.armor += item["value"]
        elif item["type"] == "damage":
            for gun in player.guns:
                gun.damage = int(gun.damage * item["value"])
        elif item["type"] == "speed":
            player.speed = int(player.speed * item["value"])
        elif item["type"] == "max_health":
            player.max_health += item["value"]
            player.health += item["value"]  # Also restore the health
        elif item["type"] == "ammo":
            for gun in player.guns:
                if gun.ammo > 0:  # Only refill guns that use ammo
                    gun.ammo = min(gun.ammo + item["value"], 99)
    
    def draw(self, screen):
        if not self.is_open:
            return
            
        # Dark overlay
        overlay = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(BLACK)
        screen.blit(overlay, (0, 0))
        
        # Shop window - responsive sizing
        shop_width = int(GAME_WIDTH * 0.7)  # 70% of screen width
        shop_height = int(GAME_HEIGHT * 0.75)  # 75% of screen height
        shop_x = (GAME_WIDTH - shop_width) // 2
        shop_y = (GAME_HEIGHT - shop_height) // 2
        
        # Shop background
        pygame.draw.rect(screen, (40, 40, 60), (shop_x, shop_y, shop_width, shop_height))
        pygame.draw.rect(screen, WHITE, (shop_x, shop_y, shop_width, shop_height), 2)
        
        # Shop title - responsive font
        font_size = max(12, int(GAME_HEIGHT * 0.06))  # 6% of screen height
        font = pygame.font.Font(None, font_size)
        title_text = font.render("GUNGEON SHOP", True, GOLD)
        title_rect = title_text.get_rect(center=(shop_x + shop_width//2, shop_y + int(GAME_HEIGHT * 0.04)))
        screen.blit(title_text, title_rect)
        
        # Items - responsive positioning and font
        item_font_size = max(10, int(GAME_HEIGHT * 0.04))  # 4% of screen height
        small_font = pygame.font.Font(None, item_font_size)
        item_y = shop_y + int(GAME_HEIGHT * 0.1)
        item_spacing = int(GAME_HEIGHT * 0.08)
        
        for i, item in enumerate(self.items):
            color = WHITE if i == self.selected_item else GRAY
            
            # Item name and price
            item_text = f"{item['name']} - ${item['price']}"
            item_surface = small_font.render(item_text, True, color)
            screen.blit(item_surface, (shop_x + int(GAME_WIDTH * 0.03), item_y + i * item_spacing))
            
            # Description
            desc_surface = small_font.render(item['description'], True, color)
            screen.blit(desc_surface, (shop_x + int(GAME_WIDTH * 0.03), item_y + i * item_spacing + int(GAME_HEIGHT * 0.03)))
        
        # Instructions - responsive positioning
        instruction_font_size = max(8, int(GAME_HEIGHT * 0.035))
        inst_font = pygame.font.Font(None, instruction_font_size)
        instructions = "Use W/S to select, ENTER to buy, TAB to close"
        inst_surface = inst_font.render(instructions, True, WHITE)
        inst_rect = inst_surface.get_rect(center=(shop_x + shop_width//2, shop_y + shop_height - int(GAME_HEIGHT * 0.05)))
        screen.blit(inst_surface, inst_rect)

class SpawnRoom:
    def __init__(self):
        self.width = 15
        self.height = 12
        self.walls = set()
        self.floor_tiles = set()
        self.doors = []
        
        self.generate_spawn_room()
        
    def generate_spawn_room(self):
        # Create floor
        for x in range(1, self.width - 1):
            for y in range(1, self.height - 1):
                self.floor_tiles.add((x, y))
        
        # Create walls around perimeter
        for x in range(self.width):
            self.walls.add((x, 0))
            self.walls.add((x, self.height - 1))
        for y in range(self.height):
            self.walls.add((0, y))
            self.walls.add((self.width - 1, y))
        
        # Create door opening in the bottom wall
        door_x = self.width // 2 - 1
        door_y = self.height - 1
        
        # Remove wall tiles for door opening
        self.walls.discard((door_x, door_y))
        self.walls.discard((door_x + 1, door_y))
        
        # Add the actual door
        door = Door(door_x * 16, door_y * 16, "horizontal")
        self.doors.append(door)
    
    def update(self, dt, player_pos):
        # Update doors based on player proximity
        for door in self.doors:
            distance_to_door = math.sqrt((player_pos.x - (door.x + door.width/2))**2 + 
                                       (player_pos.y - (door.y + door.height/2))**2)
            player_nearby = distance_to_door < 40
            door.update(dt, player_nearby)
    
    def check_door_collision(self, player_pos, player_size):
        for door in self.doors:
            collision_rect = door.get_collision_rect()
            if collision_rect:
                door_x, door_y, door_w, door_h = collision_rect
                if (player_pos.x - player_size/2 < door_x + door_w and
                    player_pos.x + player_size/2 > door_x and
                    player_pos.y - player_size/2 < door_y + door_h and
                    player_pos.y + player_size/2 > door_y):
                    return True
        return False
    
    def check_transition(self, player_pos):
        # Check if player has moved through the door to transition to combat
        if player_pos.y > (self.height - 1) * 16 + 8:  # Past the door
            return True
        return False
    
    def draw(self, screen, camera, game_instance=None):
        # Draw spawn room floor with mystical overlay
        for x, y in self.floor_tiles:
            screen_x = x * 16 - camera.x
            screen_y = y * 16 - camera.y
            # Create mystical floor overlay
            floor_surface = pygame.Surface((16, 16))
            floor_surface.set_alpha(140)  # Semi-transparent
            floor_surface.fill((SPAWN_FLOOR[0] + 15, SPAWN_FLOOR[1] + 15, SPAWN_FLOOR[2] + 15))
            screen.blit(floor_surface, (screen_x, screen_y))
        
        # Draw spawn room walls with enhanced mystical appearance
        for x, y in self.walls:
            screen_x = x * 16 - camera.x
            screen_y = y * 16 - camera.y
            # Main wall
            pygame.draw.rect(screen, SPAWN_WALL, (screen_x, screen_y, 16, 16))
            # Mystical glow border
            pygame.draw.rect(screen, (SPAWN_WALL[0] + 20, SPAWN_WALL[1] + 20, SPAWN_WALL[2] + 30), (screen_x, screen_y, 16, 16), 2)
            # Inner mystical highlight
            pygame.draw.rect(screen, (SPAWN_WALL[0] + 30, SPAWN_WALL[1] + 30, SPAWN_WALL[2] + 40), (screen_x + 2, screen_y + 2, 12, 12), 1)
        
        # Draw doors
        for door in self.doors:
            door.draw(screen, camera)
        
        # Draw instructional text in spawn room
        if camera.y < 50:  # Only show when camera is in spawn area
            if game_instance and hasattr(game_instance, 'current_level') and hasattr(game_instance, 'rooms_cleared_this_level'):
                level = game_instance.current_level
                rooms_cleared = game_instance.rooms_cleared_this_level
                rooms_per_level = game_instance.rooms_per_level
                
                if rooms_cleared == 0:
                    instruction_text = f"Level {level} - Enter the door to face your first challenge!"
                elif rooms_cleared < rooms_per_level:
                    instruction_text = f"Level {level} - Room {rooms_cleared + 1}/{rooms_per_level} awaits!"
                else:
                    instruction_text = f"Level {level} complete! Next level awaits!"
            else:
                instruction_text = "Approach the door to enter combat"
                
            font = pygame.font.Font(None, 16)
            text_surface = font.render(instruction_text, True, WHITE)
            text_rect = text_surface.get_rect(center=(GAME_WIDTH//2, 40))
            screen.blit(text_surface, text_rect)

class BackgroundParticle:
    def __init__(self, x, y, particle_type="dust"):
        self.pos = Vector2(x, y)
        self.particle_type = particle_type
        self.age = 0.0
        self.max_age = random.uniform(3.0, 8.0)
        self.alpha = random.randint(50, 150)
        
        if particle_type == "dust":
            self.velocity = Vector2(random.uniform(-10, 10), random.uniform(-5, 5))
            self.size = random.randint(1, 3)
            self.color = random.choice([(80, 70, 60), (90, 80, 70), (70, 60, 50)])
        elif particle_type == "ember":
            self.velocity = Vector2(random.uniform(-15, 15), random.uniform(-20, -5))
            self.size = random.randint(2, 4)
            self.color = random.choice([(255, 100, 0), (255, 140, 0), (255, 69, 0)])
        elif particle_type == "magic":
            self.velocity = Vector2(random.uniform(-8, 8), random.uniform(-8, 8))
            self.size = random.randint(1, 2)
            self.color = random.choice([(100, 150, 255), (150, 100, 255), (200, 150, 255)])
    
    def update(self, dt):
        self.pos = self.pos + self.velocity * dt
        self.age += dt
        
        # Fade out over time
        fade_ratio = 1.0 - (self.age / self.max_age)
        self.alpha = int(fade_ratio * 150)
        
        # Gravity for embers
        if self.particle_type == "ember":
            self.velocity.y += 20 * dt
        
        return self.age < self.max_age
    
    def draw(self, screen, camera):
        if self.alpha <= 0:
            return
        
        screen_x = int(self.pos.x - camera.x)
        screen_y = int(self.pos.y - camera.y)
        
        # Create surface with alpha
        particle_surface = pygame.Surface((self.size * 2, self.size * 2))
        particle_surface.set_alpha(self.alpha)
        particle_surface.fill(self.color)
        
        screen.blit(particle_surface, (screen_x - self.size, screen_y - self.size))

class BackgroundSystem:
    def __init__(self):
        self.particles = []
        self.torch_positions = []
        self.crack_patterns = []
        self.moss_patches = []
        self.stone_details = []
        self.animation_time = 0.0
        self.generate_details()
    
    def generate_details(self):
        """Generate static background details"""
        # Generate torch positions (every 100-150 pixels along walls)
        for x in range(0, 800, random.randint(100, 150)):
            for y in range(0, 600, random.randint(120, 180)):
                if random.random() < 0.3:  # 30% chance for torch
                    self.torch_positions.append((x, y))
        
        # Generate crack patterns
        for _ in range(50):
            start_x = random.randint(0, 800)
            start_y = random.randint(0, 600)
            length = random.randint(20, 80)
            angle = random.uniform(0, math.pi * 2)
            end_x = start_x + math.cos(angle) * length
            end_y = start_y + math.sin(angle) * length
            self.crack_patterns.append(((start_x, start_y), (end_x, end_y)))
        
        # Generate moss patches
        for _ in range(30):
            x = random.randint(0, 800)
            y = random.randint(0, 600)
            size = random.randint(10, 25)
            self.moss_patches.append((x, y, size))
        
        # Generate stone details (small decorative elements)
        for _ in range(100):
            x = random.randint(0, 800)
            y = random.randint(0, 600)
            detail_type = random.choice(["pebble", "indent", "highlight"])
            size = random.randint(2, 8)
            self.stone_details.append((x, y, detail_type, size))
    
    def update(self, dt, camera):
        self.animation_time += dt
        
        # Update particles
        self.particles = [p for p in self.particles if p.update(dt)]
        
        # Spawn new particles occasionally
        if random.random() < 0.1:  # 10% chance per frame
            # Spawn dust particles
            if random.random() < 0.7:
                x = camera.x + random.randint(-50, GAME_WIDTH + 50)
                y = camera.y + random.randint(-50, GAME_HEIGHT + 50)
                self.particles.append(BackgroundParticle(x, y, "dust"))
        
        # Spawn ember particles near torches
        for torch_x, torch_y in self.torch_positions:
            if random.random() < 0.3:  # 30% chance per torch per frame
                x = torch_x + random.randint(-5, 5)
                y = torch_y + random.randint(-5, 5)
                self.particles.append(BackgroundParticle(x, y, "ember"))
        
        # Spawn magical particles occasionally
        if random.random() < 0.05:
            x = camera.x + random.randint(0, GAME_WIDTH)
            y = camera.y + random.randint(0, GAME_HEIGHT)
            self.particles.append(BackgroundParticle(x, y, "magic"))
    
    def draw_background_layers(self, screen, camera):
        """Draw multiple background layers for depth"""
        
        # Layer 1: Deep background with gradient
        self.draw_gradient_background(screen)
        
        # Layer 2: Stone texture base
        self.draw_stone_texture(screen, camera)
        
        # Layer 3: Architectural details
        self.draw_architectural_details(screen, camera)
        
        # Layer 4: Environmental details (cracks, moss, etc.)
        self.draw_environmental_details(screen, camera)
        
        # Layer 5: Lighting effects
        self.draw_lighting_effects(screen, camera)
        
        # Layer 6: Particles
        for particle in self.particles:
            particle.draw(screen, camera)
    
    def draw_gradient_background(self, screen):
        """Draw a subtle gradient background"""
        for y in range(GAME_HEIGHT):
            # Create vertical gradient from dark to slightly lighter
            ratio = y / GAME_HEIGHT
            r = int(DUNGEON_DARK[0] + (DUNGEON_ACCENT[0] - DUNGEON_DARK[0]) * ratio)
            g = int(DUNGEON_DARK[1] + (DUNGEON_ACCENT[1] - DUNGEON_DARK[1]) * ratio)
            b = int(DUNGEON_DARK[2] + (DUNGEON_ACCENT[2] - DUNGEON_DARK[2]) * ratio)
            pygame.draw.line(screen, (r, g, b), (0, y), (GAME_WIDTH, y))
    
    def draw_stone_texture(self, screen, camera):
        """Draw detailed stone texture"""
        # Draw stone blocks pattern
        block_size = 32
        offset_x = int(camera.x) % block_size
        offset_y = int(camera.y) % block_size
        
        for x in range(-offset_x, GAME_WIDTH + block_size, block_size):
            for y in range(-offset_y, GAME_HEIGHT + block_size, block_size):
                # Use deterministic color variation based on position to prevent jittering
                world_x = int(camera.x) + x
                world_y = int(camera.y) + y
                color_seed = (world_x // block_size + world_y // block_size) % 21 - 10  # -10 to 10
                
                stone_color = (
                    max(0, min(255, STONE_LIGHT[0] + color_seed)),
                    max(0, min(255, STONE_LIGHT[1] + color_seed)),
                    max(0, min(255, STONE_LIGHT[2] + color_seed))
                )
                
                # Draw stone block
                pygame.draw.rect(screen, stone_color, (x, y, block_size-1, block_size-1))
                
                # Add darker border for depth
                pygame.draw.rect(screen, STONE_DARK, (x, y, block_size, block_size), 1)
                
                # Add subtle inner highlight - deterministic based on position
                highlight_chance = ((world_x // block_size) * 7 + (world_y // block_size) * 11) % 10
                if highlight_chance < 3:  # 30% chance, but deterministic
                    highlight_color = (
                        min(255, stone_color[0] + 15),
                        min(255, stone_color[1] + 15),
                        min(255, stone_color[2] + 15)
                    )
                    pygame.draw.rect(screen, highlight_color, (x+2, y+2, block_size-6, block_size-6), 1)
    
    def draw_architectural_details(self, screen, camera):
        """Draw architectural elements like pillars, arches, etc."""
        # Draw pillars at regular intervals
        pillar_spacing = 150
        pillar_width = 12
        pillar_height = GAME_HEIGHT
        
        camera_offset_x = int(camera.x)
        start_pillar = (camera_offset_x // pillar_spacing) * pillar_spacing
        
        for pillar_x in range(start_pillar - pillar_spacing, start_pillar + GAME_WIDTH + pillar_spacing * 2, pillar_spacing):
            screen_x = pillar_x - camera_offset_x
            
            if -pillar_width <= screen_x <= GAME_WIDTH:
                # Main pillar body
                pygame.draw.rect(screen, STONE_LIGHT, (screen_x, 0, pillar_width, pillar_height))
                
                # Pillar highlights and shadows
                pygame.draw.line(screen, (STONE_LIGHT[0] + 20, STONE_LIGHT[1] + 20, STONE_LIGHT[2] + 20), 
                               (screen_x + 1, 0), (screen_x + 1, pillar_height), 2)
                pygame.draw.line(screen, STONE_DARK, 
                               (screen_x + pillar_width - 1, 0), (screen_x + pillar_width - 1, pillar_height), 2)
                
                # Decorative bands on pillars
                for band_y in range(40, pillar_height, 80):
                    pygame.draw.rect(screen, STONE_DARK, (screen_x - 2, band_y, pillar_width + 4, 6))
                    pygame.draw.rect(screen, (STONE_LIGHT[0] + 10, STONE_LIGHT[1] + 10, STONE_LIGHT[2] + 10), 
                                   (screen_x - 1, band_y + 1, pillar_width + 2, 4))
    
    def draw_environmental_details(self, screen, camera):
        """Draw cracks, moss, stains, and other environmental details"""
        
        # Draw crack patterns
        for (start_pos, end_pos) in self.crack_patterns:
            start_screen = (start_pos[0] - camera.x, start_pos[1] - camera.y)
            end_screen = (end_pos[0] - camera.x, end_pos[1] - camera.y)
            
            # Only draw if visible on screen
            if (-50 <= start_screen[0] <= GAME_WIDTH + 50 and -50 <= start_screen[1] <= GAME_HEIGHT + 50):
                pygame.draw.line(screen, STONE_DARK, start_screen, end_screen, 1)
                # Add subtle glow to cracks
                pygame.draw.line(screen, (STONE_DARK[0] + 10, STONE_DARK[1] + 10, STONE_DARK[2] + 10), 
                               start_screen, end_screen, 1)
        
        # Draw moss patches
        for (moss_x, moss_y, moss_size) in self.moss_patches:
            screen_x = moss_x - camera.x
            screen_y = moss_y - camera.y
            
            if (-moss_size <= screen_x <= GAME_WIDTH + moss_size and -moss_size <= screen_y <= GAME_HEIGHT + moss_size):
                # Draw irregular moss shape
                points = []
                for i in range(8):
                    angle = (i / 8) * 2 * math.pi
                    radius = moss_size * (0.7 + 0.3 * random.random())
                    point_x = screen_x + math.cos(angle) * radius
                    point_y = screen_y + math.sin(angle) * radius
                    points.append((point_x, point_y))
                
                if len(points) > 2:
                    pygame.draw.polygon(screen, MOSS_GREEN, points)
                    # Add darker moss outline
                    pygame.draw.polygon(screen, (MOSS_GREEN[0] - 15, MOSS_GREEN[1] - 15, MOSS_GREEN[2] - 15), points, 1)
        
        # Draw stone details
        for (detail_x, detail_y, detail_type, detail_size) in self.stone_details:
            screen_x = detail_x - camera.x
            screen_y = detail_y - camera.y
            
            if (0 <= screen_x <= GAME_WIDTH and 0 <= screen_y <= GAME_HEIGHT):
                if detail_type == "pebble":
                    pygame.draw.circle(screen, STONE_DARK, (int(screen_x), int(screen_y)), detail_size)
                elif detail_type == "indent":
                    pygame.draw.circle(screen, (STONE_DARK[0] - 10, STONE_DARK[1] - 10, STONE_DARK[2] - 10), 
                                     (int(screen_x), int(screen_y)), detail_size, 1)
                elif detail_type == "highlight":
                    pygame.draw.circle(screen, (STONE_LIGHT[0] + 20, STONE_LIGHT[1] + 20, STONE_LIGHT[2] + 20), 
                                     (int(screen_x), int(screen_y)), detail_size)
    
    def draw_lighting_effects(self, screen, camera):
        """Draw torch flames and lighting effects"""
        
        for torch_x, torch_y in self.torch_positions:
            screen_x = torch_x - camera.x
            screen_y = torch_y - camera.y
            
            if (-50 <= screen_x <= GAME_WIDTH + 50 and -50 <= screen_y <= GAME_HEIGHT + 50):
                # Torch base
                pygame.draw.rect(screen, STONE_DARK, (screen_x - 2, screen_y, 4, 12))
                
                # Smaller, more realistic animated flame
                flame_flicker = math.sin(self.animation_time * 6 + torch_x * 0.1) * 0.2 + 0.8
                flame_height = int(8 * flame_flicker)  # Reduced from 15
                flame_width = int(5 * flame_flicker)   # Reduced from 8
                
                # Flame layers for depth - smaller and more refined
                # Outer flame (orange)
                flame_points = [
                    (screen_x, screen_y - 2),
                    (screen_x - flame_width//2, screen_y + flame_height//3),
                    (screen_x - flame_width//4, screen_y + flame_height),
                    (screen_x + flame_width//4, screen_y + flame_height),
                    (screen_x + flame_width//2, screen_y + flame_height//3)
                ]
                if len(flame_points) > 2:
                    pygame.draw.polygon(screen, TORCH_ORANGE, flame_points)
                
                # Inner flame (yellow) - smaller
                inner_flame_points = [
                    (screen_x, screen_y),
                    (screen_x - flame_width//3, screen_y + flame_height//3),
                    (screen_x - flame_width//6, screen_y + flame_height - 2),
                    (screen_x + flame_width//6, screen_y + flame_height - 2),
                    (screen_x + flame_width//3, screen_y + flame_height//3)
                ]
                if len(inner_flame_points) > 2:
                    pygame.draw.polygon(screen, BULLET_YELLOW, inner_flame_points)
                
                # Room illumination - larger radius but subtle
                light_radius = int(60 * flame_flicker)
                for radius in range(light_radius, 0, -10):
                    alpha = max(5, int(25 * (radius / light_radius) * flame_flicker))
                    light_surface = pygame.Surface((radius * 2, radius * 2))
                    light_surface.set_alpha(alpha)
                    light_surface.fill(TORCH_ORANGE)
                    screen.blit(light_surface, (screen_x - radius, screen_y - radius))
        
        # Reduced mystical glow effects - less intrusive
        glow_intensity = (math.sin(self.animation_time * 1.5) + 1) * 0.3  # Reduced intensity
        if glow_intensity > 0.2:
            # Create subtle mystical glow spots
            for i in range(2):  # Reduced from 3
                glow_x = (camera.x + GAME_WIDTH * 0.3 + i * GAME_WIDTH * 0.4) % (GAME_WIDTH + 100)
                glow_y = (camera.y + GAME_HEIGHT * 0.5 + math.sin(self.animation_time * 0.8 + i) * 30) % (GAME_HEIGHT + 50)
                
                glow_surface = pygame.Surface((25, 25))  # Smaller glow
                glow_surface.set_alpha(int(30 * glow_intensity))  # Reduced alpha
                glow_surface.fill(MYSTICAL_BLUE)
                screen.blit(glow_surface, (glow_x - 12, glow_y - 12))

class MenuState(Enum):
    MAIN_MENU = 1
    INSTRUCTIONS = 2
    SETTINGS = 3
    CREDITS = 4
    HIGH_SCORES = 5
    GAME = 6

class MenuParticle:
    def __init__(self):
        self.pos = Vector2(random.randint(0, GAME_WIDTH), random.randint(0, GAME_HEIGHT))
        self.velocity = Vector2(random.uniform(-20, 20), random.uniform(-30, -10))
        self.color = random.choice([
            (255, 215, 0),    # Gold
            (255, 140, 0),    # Orange
            (255, 69, 0),     # Red orange
            (100, 150, 255),  # Blue
            (150, 100, 255)   # Purple
        ])
        self.size = random.randint(2, 6)
        self.age = 0.0
        self.max_age = random.uniform(3.0, 6.0)
        self.rotation = 0.0
        self.rotation_speed = random.uniform(-5, 5)
        
    def update(self, dt):
        self.pos = self.pos + self.velocity * dt
        self.age += dt
        self.rotation += self.rotation_speed * dt
        
        # Wrap around screen
        if self.pos.x < -10:
            self.pos.x = GAME_WIDTH + 10
        elif self.pos.x > GAME_WIDTH + 10:
            self.pos.x = -10
            
        if self.pos.y < -10:
            self.pos.y = GAME_HEIGHT + 10
        elif self.pos.y > GAME_HEIGHT + 10:
            self.pos.y = -10
            
        return self.age < self.max_age
    
    def draw(self, screen):
        fade_ratio = 1.0 - (self.age / self.max_age)
        alpha = int(fade_ratio * 180)
        
        if alpha > 0:
            # Create rotated diamond shape
            points = []
            for i in range(4):
                angle = self.rotation + (i * math.pi / 2)
                x = self.pos.x + math.cos(angle) * self.size
                y = self.pos.y + math.sin(angle) * self.size
                points.append((x, y))
            
            if len(points) > 2:
                pygame.draw.polygon(screen, self.color, points)

class Button:
    def __init__(self, x, y, width, height, text, font, action=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.action = action
        self.is_hovered = False
        self.is_pressed = False
        self.hover_scale = 1.0
        self.click_scale = 1.0
        
        # Colors
        self.normal_color = (60, 80, 120)
        self.hover_color = (80, 120, 180)
        self.pressed_color = (40, 60, 100)
        self.text_color = WHITE
        self.border_color = (120, 140, 200)
        
    def update(self, dt, mouse_pos, mouse_pressed):
        self.is_hovered = self.rect.collidepoint(mouse_pos)
        
        # Smooth hover animation
        target_hover_scale = 1.1 if self.is_hovered else 1.0
        self.hover_scale += (target_hover_scale - self.hover_scale) * dt * 8
        
        # Click animation
        if self.is_hovered and mouse_pressed:
            self.is_pressed = True
            self.click_scale = 0.95
        else:
            self.is_pressed = False
            self.click_scale += (1.0 - self.click_scale) * dt * 10
            
        return self.is_hovered and mouse_pressed
    
    def draw(self, screen):
        # Calculate scaled rect
        scale = self.hover_scale * self.click_scale
        scaled_width = int(self.rect.width * scale)
        scaled_height = int(self.rect.height * scale)
        scaled_x = self.rect.centerx - scaled_width // 2
        scaled_y = self.rect.centery - scaled_height // 2
        scaled_rect = pygame.Rect(scaled_x, scaled_y, scaled_width, scaled_height)
        
        # Choose color based on state
        if self.is_pressed:
            color = self.pressed_color
        elif self.is_hovered:
            color = self.hover_color
        else:
            color = self.normal_color
        
        # Draw button shadow
        shadow_rect = pygame.Rect(scaled_rect.x + 3, scaled_rect.y + 3, scaled_rect.width, scaled_rect.height)
        pygame.draw.rect(screen, (20, 20, 20), shadow_rect, border_radius=8)
        
        # Draw main button
        pygame.draw.rect(screen, color, scaled_rect, border_radius=8)
        pygame.draw.rect(screen, self.border_color, scaled_rect, width=2, border_radius=8)
        
        # Enhanced text rendering with shadow for better visibility
        # Draw text shadow
        shadow_surface = self.font.render(self.text, True, (0, 0, 0))
        shadow_rect = shadow_surface.get_rect(center=(scaled_rect.centerx + 1, scaled_rect.centery + 1))
        screen.blit(shadow_surface, shadow_rect)
        
        # Draw main text
        text_surface = self.font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=scaled_rect.center)
        screen.blit(text_surface, text_rect)
        
        # Add glow effect if hovered
        if self.is_hovered:
            glow_surface = pygame.Surface((scaled_rect.width + 10, scaled_rect.height + 10))
            glow_surface.set_alpha(50)
            glow_surface.fill(self.hover_color)
            screen.blit(glow_surface, (scaled_rect.x - 5, scaled_rect.y - 5))

class MenuSystem:
    def __init__(self):
        self.state = MenuState.MAIN_MENU
        self.particles = []
        self.animation_time = 0.0
        self.transition_alpha = 0
        self.transitioning = False
        
        # Enhanced responsive fonts with better visibility
        base_size = int(GAME_HEIGHT * 0.05)  # Increased base font size for better visibility
        self.title_font = pygame.font.Font(None, int(base_size * 3.0))  # Larger title font
        self.large_font = pygame.font.Font(None, int(base_size * 2.0))  # Larger large font
        self.medium_font = pygame.font.Font(None, int(base_size * 1.4))  # Larger medium font
        self.small_font = pygame.font.Font(None, int(base_size * 1.1))  # Larger small font
        
        # High scores
        self.high_scores = [0, 0, 0, 0, 0]
        self.settings = {
            "master_volume": 0.7,
            "sfx_volume": 0.8,
            "music_volume": 0.6,
            "screen_shake": True,
            "particles": True
        }
        
        self.create_buttons()
        
        # Background layers
        self.background_layers = []
        self.generate_background_elements()
        
    def create_buttons(self):
        # Proportional sizing based on game dimensions
        button_width = int(GAME_WIDTH * 0.4)  # 40% of screen width
        button_height = int(GAME_HEIGHT * 0.08)  # 8% of screen height
        button_x = (GAME_WIDTH - button_width) // 2
        start_y = int(GAME_HEIGHT * 0.55)  # Start buttons at 55% down the screen
        spacing = int(GAME_HEIGHT * 0.09)  # 9% spacing between buttons
        
        self.main_menu_buttons = [
            Button(button_x, start_y, button_width, button_height, "START GAME", self.medium_font, "start_game"),
            Button(button_x, start_y + spacing, button_width, button_height, "INSTRUCTIONS", self.medium_font, "instructions"),
            Button(button_x, start_y + spacing * 2, button_width, button_height, "SETTINGS", self.medium_font, "settings"),
            Button(button_x, start_y + spacing * 3, button_width, button_height, "HIGH SCORES", self.medium_font, "high_scores"),
            Button(button_x, start_y + spacing * 4, button_width, button_height, "CREDITS", self.medium_font, "credits"),
        ]
        
        # Back button for sub-menus - responsive positioning
        back_width = int(GAME_WIDTH * 0.2)
        back_height = int(GAME_HEIGHT * 0.06)
        self.back_button = Button(int(GAME_WIDTH * 0.05), GAME_HEIGHT - back_height - int(GAME_HEIGHT * 0.05), 
                                back_width, back_height, "BACK", self.small_font, "back")
        
        # Settings buttons - responsive positioning
        settings_x = int(GAME_WIDTH * 0.1)
        settings_y = int(GAME_HEIGHT * 0.25)
        settings_spacing = int(GAME_HEIGHT * 0.12)
        settings_button_width = int(GAME_WIDTH * 0.25)
        settings_button_height = int(GAME_HEIGHT * 0.06)
        
        self.settings_buttons = [
            Button(settings_x + int(GAME_WIDTH * 0.45), settings_y, settings_button_width, settings_button_height, "Toggle", self.small_font, "toggle_shake"),
            Button(settings_x + int(GAME_WIDTH * 0.45), settings_y + settings_spacing, settings_button_width, settings_button_height, "Toggle", self.small_font, "toggle_particles"),
        ]
        
    def generate_background_elements(self):
        # Generate floating geometric shapes for background
        for _ in range(30):
            x = random.randint(0, GAME_WIDTH)
            y = random.randint(0, GAME_HEIGHT)
            size = random.randint(20, 80)
            rotation = random.uniform(0, 2 * math.pi)
            rotation_speed = random.uniform(-1, 1)
            color = random.choice([
                (40, 40, 60, 100),
                (60, 40, 80, 100),
                (80, 60, 40, 100),
                (40, 80, 60, 100)
            ])
            self.background_layers.append({
                'pos': Vector2(x, y),
                'size': size,
                'rotation': rotation,
                'rotation_speed': rotation_speed,
                'color': color,
                'shape': random.choice(['triangle', 'square', 'pentagon'])
            })
    
    def update(self, dt, mouse_pos, mouse_pressed, keys):
        self.animation_time += dt
        
        # Update particles
        if self.settings["particles"]:
            self.particles = [p for p in self.particles if p.update(dt)]
            
            # Spawn new particles
            if random.random() < 0.3:
                self.particles.append(MenuParticle())
        
        # Update background elements
        for element in self.background_layers:
            element['rotation'] += element['rotation_speed'] * dt
            # Slow floating motion
            element['pos'].x += math.sin(self.animation_time * 0.5 + element['rotation']) * 10 * dt
            element['pos'].y += math.cos(self.animation_time * 0.3 + element['rotation']) * 8 * dt
            
            # Wrap around
            if element['pos'].x < -element['size']:
                element['pos'].x = GAME_WIDTH + element['size']
            elif element['pos'].x > GAME_WIDTH + element['size']:
                element['pos'].x = -element['size']
                
            if element['pos'].y < -element['size']:
                element['pos'].y = GAME_HEIGHT + element['size']
            elif element['pos'].y > GAME_HEIGHT + element['size']:
                element['pos'].y = -element['size']
        
        # Handle button updates based on current state
        if self.state == MenuState.MAIN_MENU:
            for button in self.main_menu_buttons:
                if button.update(dt, mouse_pos, mouse_pressed):
                    return button.action
                    
        elif self.state in [MenuState.INSTRUCTIONS, MenuState.CREDITS, MenuState.HIGH_SCORES]:
            if self.back_button.update(dt, mouse_pos, mouse_pressed):
                return "back"
                
        elif self.state == MenuState.SETTINGS:
            if self.back_button.update(dt, mouse_pos, mouse_pressed):
                return "back"
            for button in self.settings_buttons:
                if button.update(dt, mouse_pos, mouse_pressed):
                    return button.action
        
        return None
    
    def draw(self, screen):
        # Draw animated gradient background
        self.draw_animated_background(screen)
        
        # Draw background elements
        self.draw_background_elements(screen)
        
        # Draw particles
        if self.settings["particles"]:
            for particle in self.particles:
                particle.draw(screen)
        
        # Draw content based on state
        if self.state == MenuState.MAIN_MENU:
            self.draw_main_menu(screen)
        elif self.state == MenuState.INSTRUCTIONS:
            self.draw_instructions(screen)
        elif self.state == MenuState.SETTINGS:
            self.draw_settings(screen)
        elif self.state == MenuState.CREDITS:
            self.draw_credits(screen)
        elif self.state == MenuState.HIGH_SCORES:
            self.draw_high_scores(screen)
    
    def draw_animated_background(self, screen):
        # Animated gradient background
        for y in range(GAME_HEIGHT):
            ratio = y / GAME_HEIGHT
            wave = math.sin(self.animation_time * 2 + ratio * 4) * 0.1
            
            r = int(20 + (35 + wave * 10) * ratio)
            g = int(15 + (25 + wave * 8) * ratio)
            b = int(25 + (45 + wave * 15) * ratio)
            
            pygame.draw.line(screen, (r, g, b), (0, y), (GAME_WIDTH, y))
    
    def draw_background_elements(self, screen):
        for element in self.background_layers:
            points = []
            if element['shape'] == 'triangle':
                for i in range(3):
                    angle = element['rotation'] + (i * 2 * math.pi / 3)
                    x = element['pos'].x + math.cos(angle) * element['size'] // 4
                    y = element['pos'].y + math.sin(angle) * element['size'] // 4
                    points.append((x, y))
            elif element['shape'] == 'square':
                for i in range(4):
                    angle = element['rotation'] + (i * math.pi / 2)
                    x = element['pos'].x + math.cos(angle) * element['size'] // 4
                    y = element['pos'].y + math.sin(angle) * element['size'] // 4
                    points.append((x, y))
            elif element['shape'] == 'pentagon':
                for i in range(5):
                    angle = element['rotation'] + (i * 2 * math.pi / 5)
                    x = element['pos'].x + math.cos(angle) * element['size'] // 4
                    y = element['pos'].y + math.sin(angle) * element['size'] // 4
                    points.append((x, y))
            
            if len(points) > 2:
                # Create surface for alpha blending
                temp_surface = pygame.Surface((element['size'], element['size']))
                temp_surface.set_colorkey((0, 0, 0))
                
                adjusted_points = [(p[0] - element['pos'].x + element['size']//2, 
                                  p[1] - element['pos'].y + element['size']//2) for p in points]
                pygame.draw.polygon(temp_surface, element['color'][:3], adjusted_points)
                temp_surface.set_alpha(element['color'][3])
                
                screen.blit(temp_surface, (element['pos'].x - element['size']//2, element['pos'].y - element['size']//2))
    
    def draw_main_menu(self, screen):
        # Enhanced animated title with better visibility
        title_text = "ENTER THE GUNGEON"
        title_y = int(GAME_HEIGHT * 0.2)  # Title at 20% down the screen
        
        # Enhanced title glow with better colours
        glow_intensity = abs(math.sin(self.animation_time * 3)) * 0.6 + 0.4
        glow_color = (int(255 * glow_intensity), int(180 * glow_intensity), 0)  # Brighter orange
        
        # Multiple glow layers for better effect
        glow_offset = max(2, int(GAME_HEIGHT * 0.015))  # Larger glow offset
        for offset in range(glow_offset, 0, -1):
            glow_surface = self.title_font.render(title_text, True, glow_color)
            glow_surface.set_alpha(80 - offset * 10)  # Higher alpha for better visibility
            glow_rect = glow_surface.get_rect(center=(GAME_WIDTH//2 + offset, title_y + offset))
            screen.blit(glow_surface, glow_rect)
        
        # Main title with enhanced colour
        title_surface = self.title_font.render(title_text, True, (255, 255, 255))  # Pure white
        title_rect = title_surface.get_rect(center=(GAME_WIDTH//2, title_y))
        screen.blit(title_surface, title_rect)
        
        # Enhanced subtitle with better visibility
        subtitle_text = "A Pixel-Perfect Bullet Hell Adventure"
        subtitle_surface = self.medium_font.render(subtitle_text, True, (220, 220, 220))  # Brighter grey
        subtitle_y = title_y + int(GAME_HEIGHT * 0.08)  # Subtitle 8% below title
        subtitle_rect = subtitle_surface.get_rect(center=(GAME_WIDTH//2, subtitle_y))
        screen.blit(subtitle_surface, subtitle_rect)
        
        # Draw buttons
        for button in self.main_menu_buttons:
            button.draw(screen)
        
        # Enhanced version info with better visibility
        version_text = "v1.0 - Made with ❤️"
        version_surface = self.small_font.render(version_text, True, (180, 180, 180))  # Brighter grey
        version_y = GAME_HEIGHT - int(GAME_HEIGHT * 0.05)
        screen.blit(version_surface, (int(GAME_WIDTH * 0.03), version_y))
    
    def draw_instructions(self, screen):
        # Enhanced title with better visibility
        title_surface = self.large_font.render("INSTRUCTIONS", True, (255, 255, 255))
        title_rect = title_surface.get_rect(center=(GAME_WIDTH//2, int(GAME_HEIGHT * 0.08)))
        screen.blit(title_surface, title_rect)
        
        # Enhanced instructions content with better colours
        instructions = [
            ("MOVEMENT", "WASD Keys", (255, 255, 0)),  # Bright yellow
            ("AIM", "Mouse", (255, 255, 0)),  # Bright yellow
            ("SHOOT", "Left Mouse Button", (255, 100, 100)),  # Bright red
            ("DODGE ROLL", "Right Mouse / Spacebar", (100, 200, 255)),  # Bright blue
            ("SWITCH WEAPON", "Q Key", (200, 100, 255)),  # Bright purple
            ("SHOP", "TAB Key", (255, 200, 100)),  # Bright orange
            ("PAUSE", "P Key", (255, 255, 255)),  # Pure white
            ("", "", (0, 0, 0)),
            ("OBJECTIVE", "Clear all rooms to advance levels!", (100, 255, 100)),  # Bright green
            ("", "Defeat the boss to win the game!", (255, 150, 150)),  # Bright red
        ]
        
        start_y = int(GAME_HEIGHT * 0.18)
        line_spacing = int(GAME_HEIGHT * 0.06)
        
        y_pos = start_y
        for category, instruction, color in instructions:
            if category:
                cat_surface = self.medium_font.render(category + ":", True, color)
                screen.blit(cat_surface, (int(GAME_WIDTH * 0.08), y_pos))
                
                if instruction:
                    inst_surface = self.small_font.render(instruction, True, (240, 240, 240))  # Very light grey
                    screen.blit(inst_surface, (int(GAME_WIDTH * 0.35), y_pos + int(GAME_HEIGHT * 0.01)))
            
            y_pos += line_spacing
        
        self.back_button.draw(screen)
    
    def draw_settings(self, screen):
        # Title - responsive positioning
        title_surface = self.large_font.render("SETTINGS", True, WHITE)
        title_rect = title_surface.get_rect(center=(GAME_WIDTH//2, int(GAME_HEIGHT * 0.08)))
        screen.blit(title_surface, title_rect)
        
        # Settings options - responsive positioning
        start_y = int(GAME_HEIGHT * 0.25)
        spacing = int(GAME_HEIGHT * 0.12)
        
        # Screen shake toggle
        shake_text = f"Screen Shake: {'ON' if self.settings['screen_shake'] else 'OFF'}"
        shake_surface = self.medium_font.render(shake_text, True, WHITE)
        screen.blit(shake_surface, (int(GAME_WIDTH * 0.1), start_y))
        self.settings_buttons[0].draw(screen)
        
        # Particles toggle
        particles_text = f"Particles: {'ON' if self.settings['particles'] else 'OFF'}"
        particles_surface = self.medium_font.render(particles_text, True, WHITE)
        screen.blit(particles_surface, (int(GAME_WIDTH * 0.1), start_y + spacing))
        self.settings_buttons[1].draw(screen)
        
        self.back_button.draw(screen)
    
    def draw_credits(self, screen):
        # Title - responsive positioning
        title_surface = self.large_font.render("CREDITS", True, WHITE)
        title_rect = title_surface.get_rect(center=(GAME_WIDTH//2, int(GAME_HEIGHT * 0.08)))
        screen.blit(title_surface, title_rect)
        
        # Credits content - responsive positioning
        credits = [
            ("GAME DESIGN & PROGRAMMING", (255, 215, 0)),
            ("AI Assistant (Claude)", (200, 200, 200)),
            ("", (0, 0, 0)),
            ("INSPIRED BY", (255, 140, 0)),
            ("Enter the Gungeon by Dodge Roll", (200, 200, 200)),
            ("", (0, 0, 0)),
            ("BUILT WITH", (100, 150, 255)),
            ("Python & Pygame", (200, 200, 200)),
            ("", (0, 0, 0)),
            ("SPECIAL THANKS", (255, 100, 100)),
            ("The indie game development community", (200, 200, 200)),
            ("Bullet hell enthusiasts everywhere", (200, 200, 200)),
        ]
        
        start_y = int(GAME_HEIGHT * 0.18)
        line_spacing = int(GAME_HEIGHT * 0.05)
        
        y_pos = start_y
        for text, color in credits:
            if text:
                if color == (200, 200, 200):
                    surface = self.small_font.render(text, True, color)
                    screen.blit(surface, (int(GAME_WIDTH * 0.12), y_pos))
                else:
                    surface = self.medium_font.render(text, True, color)
                    screen.blit(surface, (int(GAME_WIDTH * 0.08), y_pos))
            y_pos += line_spacing
        
        self.back_button.draw(screen)
    
    def draw_high_scores(self, screen):
        # Title - responsive positioning
        title_surface = self.large_font.render("HIGH SCORES", True, WHITE)
        title_rect = title_surface.get_rect(center=(GAME_WIDTH//2, int(GAME_HEIGHT * 0.08)))
        screen.blit(title_surface, title_rect)
        
        # High scores list - responsive positioning
        start_y = int(GAME_HEIGHT * 0.2)
        line_spacing = int(GAME_HEIGHT * 0.08)
        
        y_pos = start_y
        for i, score in enumerate(self.high_scores):
            rank_text = f"{i + 1}."
            score_text = f"{score:,}"
            
            rank_surface = self.medium_font.render(rank_text, True, (255, 215, 0))
            score_surface = self.medium_font.render(score_text, True, WHITE)
            
            screen.blit(rank_surface, (int(GAME_WIDTH * 0.2), y_pos))
            screen.blit(score_surface, (int(GAME_WIDTH * 0.35), y_pos))
            
            y_pos += line_spacing
        
        # Instructions - responsive positioning
        if all(score == 0 for score in self.high_scores):
            no_scores_text = "No high scores yet - start playing!"
            no_scores_surface = self.small_font.render(no_scores_text, True, (128, 128, 128))
            no_scores_rect = no_scores_surface.get_rect(center=(GAME_WIDTH//2, y_pos + int(GAME_HEIGHT * 0.05)))
            screen.blit(no_scores_surface, no_scores_rect)
        
        self.back_button.draw(screen)
    
    def handle_action(self, action):
        if action == "start_game":
            return MenuState.GAME
        elif action == "instructions":
            self.state = MenuState.INSTRUCTIONS
        elif action == "settings":
            self.state = MenuState.SETTINGS
        elif action == "credits":
            self.state = MenuState.CREDITS
        elif action == "high_scores":
            self.state = MenuState.HIGH_SCORES
        elif action == "back":
            self.state = MenuState.MAIN_MENU
        elif action == "toggle_shake":
            self.settings["screen_shake"] = not self.settings["screen_shake"]
        elif action == "toggle_particles":
            self.settings["particles"] = not self.settings["particles"]
        
        return None
    
    def add_high_score(self, score):
        self.high_scores.append(score)
        self.high_scores.sort(reverse=True)
        self.high_scores = self.high_scores[:5]

class GungeonGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
        self.game_surface = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
        pygame.display.set_caption("Enter the Gungeon")
        self.clock = pygame.time.Clock()
        self.running = True
        self.current_screen_width = SCREEN_WIDTH
        self.current_screen_height = SCREEN_HEIGHT
        
        # Menu system
        self.menu_system = MenuSystem()
        self.game_state = MenuState.MAIN_MENU
        self.mouse_pressed_this_frame = False
        
        # Game objects - initialize when starting game
        self.player = None
        self.camera = None
        self.multi_room_system = None
        self.spawn_room = None
        
        self.keys = {}
        self.mouse_pos = (0, 0)
        self.mouse_pressed = False
        
        # Enhanced game fonts with better visibility
        self.font = pygame.font.Font(None, 32)  # Increased from 24
        self.small_font = pygame.font.Font(None, 20)  # Increased from 16
        
        # Game state variables
        self.paused = False
        self.game_over = False
        self.game_over_timer = 0.0
        self.final_score = 0
        self.survival_time = 0.0
        self.enemies_killed = 0
        self.start_time = 0
        
        # Game state management
        self.in_spawn_room = True
        self.in_multi_room_system = False
        self.transition_offset = 0
        self.respawn_button_rect = None
        
        # Level system
        self.current_level = 1
        self.max_level = 10
        self.rooms_cleared_this_level = 0
        self.rooms_per_level = 3
        
        # Shop system
        self.shop = None
        
        # Objectives system
        self.objectives = []
        self.total_rooms_cleared = 0
        
        # Background system
        self.background = None
        
        print("=== ENTER THE GUNGEON ===")
        print("Navigate the menus to start your adventure!")
        print("===============================")
        
    def initialize_game(self):
        """Initialize game objects when starting a new game"""
        self.player = Player(120, 96)  # Center of smaller spawn room
        self.camera = Camera()
        
        # Replace single room with multi-room system
        self.multi_room_system = MultiRoomSystem(level=1)
        self.spawn_room = SpawnRoom()
        
        # Game state variables
        self.paused = False
        self.game_over = False
        self.game_over_timer = 0.0
        self.final_score = 0
        self.survival_time = 0.0
        self.enemies_killed = 0
        self.start_time = time.time()
        
        # Game state management
        self.in_spawn_room = True
        self.in_multi_room_system = False
        self.transition_offset = 0
        self.respawn_button_rect = None
        
        # Level system
        self.current_level = 1
        self.rooms_cleared_this_level = 0
        
        # Shop system
        self.shop = Shop()
        
        # Objectives system
        self.objectives = [
            {"name": "Clear 5 rooms", "target": 5, "current": 0, "type": "rooms", "reward": 50, "completed": False},
            {"name": "Kill 25 enemies", "target": 25, "current": 0, "type": "kills", "reward": 75, "completed": False},
            {"name": "Reach Level 3", "target": 3, "current": 1, "type": "level", "reward": 100, "completed": False},
            {"name": "Survive 5 minutes", "target": 300, "current": 0, "type": "time", "reward": 125, "completed": False}
        ]
        self.total_rooms_cleared = 0
        
        # Background system
        self.background = BackgroundSystem()
        
        print("🚀 New game started! Good luck, gunslinger!")
        print("=============================")
    
    def handle_events(self):
        self.mouse_pressed_this_frame = False
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.VIDEORESIZE:
                # Handle window resizing
                self.current_screen_width = event.w
                self.current_screen_height = event.h
                self.screen = pygame.display.set_mode((self.current_screen_width, self.current_screen_height), pygame.RESIZABLE)
                # Recreate menu system with new responsive sizing
                if hasattr(self, 'menu_system'):
                    self.menu_system = MenuSystem()
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.game_state == MenuState.GAME:
                        # Return to main menu during game
                        self.game_state = MenuState.MAIN_MENU
                        self.menu_system.state = MenuState.MAIN_MENU
                    else:
                        # Quit from menu
                        self.running = False
                
                # Game-specific controls (only when in game)
                if self.game_state == MenuState.GAME and self.player:
                    if event.key == pygame.K_p:
                        self.paused = not self.paused
                    elif event.key == pygame.K_w:
                        self.keys['up'] = True
                    elif event.key == pygame.K_s:
                        self.keys['down'] = True
                    elif event.key == pygame.K_a:
                        self.keys['left'] = True
                    elif event.key == pygame.K_d:
                        self.keys['right'] = True
                    elif event.key == pygame.K_SPACE:
                        self.player.dodge_roll()
                    elif event.key == pygame.K_q:
                        self.player.switch_weapon()
                    elif event.key == pygame.K_r and self.game_over:
                        self.restart_game()
                    elif event.key == pygame.K_TAB and self.shop:
                        self.shop.toggle()
                    elif event.key == pygame.K_RETURN and self.shop and self.shop.is_open:
                        if self.shop.buy_item(self.player, self.shop.selected_item):
                            print(f"Purchased {self.shop.items[self.shop.selected_item]['name']}!")
                    elif self.shop and self.shop.is_open:
                        if event.key == pygame.K_w:
                            self.shop.selected_item = (self.shop.selected_item - 1) % len(self.shop.items)
                        elif event.key == pygame.K_s:
                            self.shop.selected_item = (self.shop.selected_item + 1) % len(self.shop.items)
            
            elif event.type == pygame.KEYUP:
                if self.game_state == MenuState.GAME:
                    if event.key == pygame.K_w:
                        self.keys['up'] = False
                    elif event.key == pygame.K_s:
                        self.keys['down'] = False
                    elif event.key == pygame.K_a:
                        self.keys['left'] = False
                    elif event.key == pygame.K_d:
                        self.keys['right'] = False
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.mouse_pressed_this_frame = True
                    if self.game_state == MenuState.GAME:
                        if self.game_over and self.respawn_button_rect:
                            # Check if click is on respawn button with proper scaling
                            scale_x = self.current_screen_width / GAME_WIDTH
                            scale_y = self.current_screen_height / GAME_HEIGHT
                            scale = min(scale_x, scale_y)
                            
                            scaled_width = int(GAME_WIDTH * scale)
                            scaled_height = int(GAME_HEIGHT * scale)
                            offset_x = (self.current_screen_width - scaled_width) // 2
                            offset_y = (self.current_screen_height - scaled_height) // 2
                            
                            adjusted_x = (event.pos[0] - offset_x) / scale
                            adjusted_y = (event.pos[1] - offset_y) / scale
                            
                            if self.respawn_button_rect.collidepoint(adjusted_x, adjusted_y):
                                self.restart_game()
                        else:
                            self.mouse_pressed = True
                elif event.button == 3:
                    if self.game_state == MenuState.GAME and not self.game_over and self.player:
                        self.player.dodge_roll()
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and self.game_state == MenuState.GAME:
                    self.mouse_pressed = False
            
            elif event.type == pygame.MOUSEMOTION:
                # Calculate mouse position accounting for scaling and letterboxing
                scale_x = self.current_screen_width / GAME_WIDTH
                scale_y = self.current_screen_height / GAME_HEIGHT
                scale = min(scale_x, scale_y)
                
                scaled_width = int(GAME_WIDTH * scale)
                scaled_height = int(GAME_HEIGHT * scale)
                offset_x = (self.current_screen_width - scaled_width) // 2
                offset_y = (self.current_screen_height - scaled_height) // 2
                
                # Adjust mouse coordinates
                adjusted_x = (event.pos[0] - offset_x) / scale
                adjusted_y = (event.pos[1] - offset_y) / scale
                
                # Clamp to game bounds
                game_mouse_x = max(0, min(GAME_WIDTH, adjusted_x))
                game_mouse_y = max(0, min(GAME_HEIGHT, adjusted_y))
                self.mouse_pos = (game_mouse_x, game_mouse_y)
    
    def update(self, dt):
        # Handle menu state
        if self.game_state != MenuState.GAME:
            action = self.menu_system.update(dt, self.mouse_pos, self.mouse_pressed_this_frame, self.keys)
            if action:
                new_state = self.menu_system.handle_action(action)
                if new_state == MenuState.GAME:
                    self.game_state = MenuState.GAME
                    self.initialize_game()
            return
        
        # Game logic - only runs when in game state
        if self.paused or self.game_over or not self.player:
            return
        
        # Handle room-specific logic
        if self.in_spawn_room:
            # Update spawn room
            self.spawn_room.update(dt, self.player.pos)
            
            # Check for door collisions in spawn room
            old_pos = Vector2(self.player.pos.x, self.player.pos.y)
            
            if self.mouse_pressed:
                bullets = self.player.fire_weapon()
                # Don't add bullets in spawn room
            
            self.player.update(dt, self.keys, self.mouse_pos, self.camera)
            
            # Check collision with spawn room walls
            tile_x = int(self.player.pos.x // 16)
            tile_y = int(self.player.pos.y // 16)
            if (tile_x, tile_y) in self.spawn_room.walls:
                self.player.pos = old_pos
            
            # Check door collision
            if self.spawn_room.check_door_collision(self.player.pos, self.player.size):
                self.player.pos = old_pos
            
            # Check for transition to combat room
            if self.spawn_room.check_transition(self.player.pos):
                self.transition_to_combat()
            
            # Check teleporter interaction
            if self.multi_room_system.teleporter_active:
                teleporter_pos = Vector2(120, 96)  # Center of smaller spawn room
                if self.player.pos.distance_to(teleporter_pos) < 25:
                    # Teleport to boss room
                    self.in_spawn_room = False
                    self.in_multi_room_system = True
                    self.multi_room_system.current_room_id = "boss_room"
                    self.player.pos = Vector2(240, 320)  # Adjusted for smaller boss room
                    # Spawn boss if not already spawned
                    boss_room = self.multi_room_system.get_current_room()
                    if hasattr(boss_room, 'spawn_boss'):
                        boss_room.spawn_boss()
                    print("⚡ Teleported to boss room!")
        
        else:
            # Combat room logic
            if self.mouse_pressed:
                bullets = self.player.fire_weapon()
                for bullet in bullets:
                    self.multi_room_system.get_current_room().add_player_bullet(bullet)
            
            self.player.update(dt, self.keys, self.mouse_pos, self.camera)
            self.multi_room_system.update(dt, self.player)
            # Update collision detection with game instance for kill tracking
            self.multi_room_system.get_current_room().check_collisions(self.player, self)
            
            # Check hazard damage if in hazard room
            current_room = self.multi_room_system.get_current_room()
            if isinstance(current_room, HazardRoom):
                current_room.check_hazard_damage(self.player)
            
            # Check player collision with walls
            self.check_player_wall_collisions()
            
            # Check if all rooms are cleared for level progression
            if len(self.multi_room_system.rooms_cleared) >= self.multi_room_system.total_rooms:
                if not hasattr(self, 'level_complete_timer'):
                    self.level_complete_timer = 0.0
                    print(f"🎉 All rooms cleared! Level {self.current_level} complete!")
                
                self.level_complete_timer += dt
                
                # After 3 seconds, advance level
                if self.level_complete_timer > 3.0:
                    self.advance_level()
                    # Reset room system for new level
                    self.multi_room_system = MultiRoomSystem(level=self.current_level)
                    self.return_to_spawn()
                    if hasattr(self, 'level_complete_timer'):
                        delattr(self, 'level_complete_timer')
            
            if self.player.health <= 0 and not self.game_over:
                self.game_over = True
                self.game_over_timer = 0.0
                self.survival_time = time.time() - self.start_time
                self.final_score = self.player.money * 10 + self.enemies_killed * 50 + int(self.survival_time * 5)
        
        # Update camera
        self.camera.follow(self.player.pos.x, self.player.pos.y)
        self.camera.update(dt)
        
        # Update objectives continuously
        self.update_objectives()
        
        # Update background system
        self.background.update(dt, self.camera)
        
        if self.game_over:
            self.game_over_timer += dt
    
    def transition_to_combat(self):
        """Transition from spawn room to combat room"""
        self.in_spawn_room = False
        self.in_multi_room_system = True
        # Move player to first room
        self.player.pos = Vector2(200, 200)
        self.multi_room_system.current_room_id = "room_1"
        # Start first wave
        current_room = self.multi_room_system.get_current_room()
        if hasattr(self, 'room_clear_timer'):
            delattr(self, 'room_clear_timer')
        print("🏰 Entered the multi-room dungeon!")
    
    def advance_level(self):
        """Advance to the next level"""
        if self.current_level < self.max_level:
            self.current_level += 1
            self.rooms_cleared_this_level = 0
            print(f"🎉 LEVEL UP! Now on Level {self.current_level}")
            
            # Give player some bonus rewards for leveling up
            self.player.money += 20 * self.current_level
            
            # Restore some health on level up (but not full)
            health_restore = min(30, self.player.max_health - self.player.health)
            self.player.health += health_restore
            
        else:
            print(f"🏆 CONGRATULATIONS! You've completed all {self.max_level} levels!")
    
    def return_to_spawn(self):
        """Return player to spawn room after clearing a combat room"""
        self.in_spawn_room = True
        self.player.pos = Vector2(160, 120)  # Center of spawn room
        print("Returned to spawn room. Approach the door for the next challenge!")
    
    def check_player_wall_collisions(self):
        """Check and fix player collisions with walls"""
        player_size = self.player.size
        
        if self.in_spawn_room:
            walls = self.spawn_room.walls
            room_width = self.spawn_room.width * 16
            room_height = self.spawn_room.height * 16
            hazard_tiles = set()
        else:
            current_room = self.multi_room_system.get_current_room()
            walls = current_room.walls
            room_width = current_room.width * 16
            room_height = current_room.height * 16
            
            # Add hazard tiles as obstacles (except when dodging)
            hazard_tiles = set()
            if isinstance(current_room, HazardRoom) and not self.player.is_dodging:
                hazard_tiles.update(current_room.ditches)
                hazard_tiles.update(current_room.spikes)
                hazard_tiles.update(current_room.lava_tiles)
        
        # Check collision with walls
        player_tile_x = int(self.player.pos.x // 16)
        player_tile_y = int(self.player.pos.y // 16)
        
        # Check if player is overlapping with any wall tile or hazard tile
        collision_tiles = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                check_x = player_tile_x + dx
                check_y = player_tile_y + dy
                
                # Check walls and hazard tiles (hazard tiles act as walls when not dodging)
                if (check_x, check_y) in walls or (check_x, check_y) in hazard_tiles:
                    # Check if actually colliding
                    tile_center_x = check_x * 16 + 8
                    tile_center_y = check_y * 16 + 8
                    distance = Vector2(tile_center_x, tile_center_y).distance_to(self.player.pos)
                    if distance < player_size + 8:  # Tile is 16x16, so radius is 8
                        collision_tiles.append((check_x, check_y, tile_center_x, tile_center_y))
        
        # Push player away from colliding tiles
        if collision_tiles:
            push_x = 0
            push_y = 0
            for tile_x, tile_y, center_x, center_y in collision_tiles:
                # Calculate push direction
                dx = self.player.pos.x - center_x
                dy = self.player.pos.y - center_y
                distance = math.sqrt(dx*dx + dy*dy)
                if distance > 0:
                    # Normalize and scale push
                    push_strength = (player_size + 8) - distance + 2
                    push_x += (dx / distance) * push_strength
                    push_y += (dy / distance) * push_strength
            
            # Apply push
            self.player.pos.x += push_x * 0.5
            self.player.pos.y += push_y * 0.5
        
        # Also check room boundaries
        margin = player_size
        if self.player.pos.x < margin:
            self.player.pos.x = margin
        elif self.player.pos.x > room_width - margin:
            self.player.pos.x = room_width - margin
            
        if self.player.pos.y < margin:
            self.player.pos.y = margin
        elif self.player.pos.y > room_height - margin:
            self.player.pos.y = room_height - margin
    
    def restart_game(self):
        if self.game_over:
            # Add final score to high scores before restarting
            self.menu_system.add_high_score(self.final_score)
        
        # Reset to main menu or reinitialize game
        self.initialize_game()
    
    def draw_ui(self):
        # Health bar background - smaller size
        health_bar_width = 120  # Reduced from 200
        health_bar_height = 12  # Reduced from 20
        health_bar_x = 8
        health_bar_y = 8
        
        # Draw health bar background
        pygame.draw.rect(self.game_surface, DARK_GRAY, (health_bar_x, health_bar_y, health_bar_width, health_bar_height))
        pygame.draw.rect(self.game_surface, WHITE, (health_bar_x, health_bar_y, health_bar_width, health_bar_height), 1)
        
        # Draw current health
        health_ratio = self.player.health / self.player.max_health
        current_health_width = int(health_bar_width * health_ratio)
        if current_health_width > 0:
            health_color = HEALTH_RED
            if health_ratio > 0.6:
                health_color = (0, 200, 0)  # Green when healthy
            elif health_ratio > 0.3:
                health_color = (255, 165, 0)  # Orange when medium health
            
            pygame.draw.rect(self.game_surface, health_color, (health_bar_x, health_bar_y, current_health_width, health_bar_height))
        
        # Enhanced health text with shadow for better visibility
        health_text = f"HP: {self.player.health}/{self.player.max_health}"
        # Shadow
        shadow_surface = self.small_font.render(health_text, True, (0, 0, 0))
        self.game_surface.blit(shadow_surface, (health_bar_x + health_bar_width + 6, health_bar_y + 1))
        # Main text
        health_surface = self.small_font.render(health_text, True, (255, 255, 255))
        self.game_surface.blit(health_surface, (health_bar_x + health_bar_width + 5, health_bar_y))
        
        # Armor
        for i in range(self.player.armor):
            x = 8 + i * 10  # Reduced spacing
            y = 25  # Moved up
            pygame.draw.rect(self.game_surface, ARMOR_BLUE, (x-2, y-2, 4, 4))  # Smaller armor icons
            pygame.draw.rect(self.game_surface, WHITE, (x-2, y-2, 4, 4), 1)
        
        # Weapon info with background - smaller
        gun = self.player.guns[self.player.current_gun]
        weapon_text = f"{gun.name}"
        if gun.ammo > 0:
            weapon_text += f" ({gun.ammo})"
        
        # Enhanced weapon text with shadow
        # Shadow
        shadow_surface = self.small_font.render(weapon_text, True, (0, 0, 0))
        self.game_surface.blit(shadow_surface, (9, 37))
        # Main text
        text_surface = self.small_font.render(weapon_text, True, (255, 255, 255))
        weapon_bg_rect = (6, 35, text_surface.get_width() + 4, text_surface.get_height() + 2)  # Smaller padding
        pygame.draw.rect(self.game_surface, (0, 0, 0, 180), weapon_bg_rect)  # Darker background
        pygame.draw.rect(self.game_surface, (200, 200, 200), weapon_bg_rect, 2)  # Brighter border
        self.game_surface.blit(text_surface, (8, 36))
        
        # Enhanced money display with shadow
        money_text = f"${self.player.money}"
        # Shadow
        shadow_surface = self.small_font.render(money_text, True, (0, 0, 0))
        self.game_surface.blit(shadow_surface, (GAME_WIDTH - shadow_surface.get_width() - 7, 8))
        # Main text
        money_surface = self.small_font.render(money_text, True, (255, 215, 0))  # Brighter gold
        money_bg_rect = (GAME_WIDTH - money_surface.get_width() - 10, 6, money_surface.get_width() + 4, money_surface.get_height() + 2)
        pygame.draw.rect(self.game_surface, (0, 0, 0, 180), money_bg_rect)  # Darker background
        pygame.draw.rect(self.game_surface, (255, 215, 0), money_bg_rect, 2)  # Brighter border
        self.game_surface.blit(money_surface, (GAME_WIDTH - money_surface.get_width() - 8, 7))
        
        # Enhanced level display with shadow
        level_text = f"Level {self.current_level}"
        if self.current_level < self.max_level:
            level_text += f" ({self.rooms_cleared_this_level}/{self.rooms_per_level})"
        else:
            level_text += " (MAX)"
        # Shadow
        shadow_surface = self.small_font.render(level_text, True, (0, 0, 0))
        self.game_surface.blit(shadow_surface, (GAME_WIDTH - shadow_surface.get_width() - 7, 24))
        # Main text
        level_surface = self.small_font.render(level_text, True, (255, 255, 255))
        level_bg_rect = (GAME_WIDTH - level_surface.get_width() - 10, 22, level_surface.get_width() + 4, level_surface.get_height() + 2)
        pygame.draw.rect(self.game_surface, (0, 0, 0, 180), level_bg_rect)  # Darker background
        pygame.draw.rect(self.game_surface, (200, 200, 200), level_bg_rect, 2)  # Brighter border
        self.game_surface.blit(level_surface, (GAME_WIDTH - level_surface.get_width() - 8, 23))
        
        # Level progress bar if not at max level - smaller
        if self.current_level < self.max_level:
            progress_bar_width = 60  # Reduced from 80
            progress_bar_height = 3  # Reduced from 4
            progress_x = GAME_WIDTH - progress_bar_width - 8
            progress_y = 38
            
            progress_ratio = self.rooms_cleared_this_level / self.rooms_per_level
            
            pygame.draw.rect(self.game_surface, DARK_GRAY, (progress_x, progress_y, progress_bar_width, progress_bar_height))
            pygame.draw.rect(self.game_surface, (100, 255, 100), (progress_x, progress_y, int(progress_bar_width * progress_ratio), progress_bar_height))
            pygame.draw.rect(self.game_surface, WHITE, (progress_x, progress_y, progress_bar_width, progress_bar_height), 1)
        
        # Dodge roll cooldown indicator - smaller
        if self.player.dodge_cooldown_timer > 0:
            dodge_progress = 1.0 - (self.player.dodge_cooldown_timer / self.player.dodge_cooldown)
            dodge_bar_width = 40  # Reduced from 60
            dodge_bar_height = 3  # Reduced from 4
            dodge_x = 8
            dodge_y = 55  # Moved down
            
            pygame.draw.rect(self.game_surface, DARK_GRAY, (dodge_x, dodge_y, dodge_bar_width, dodge_bar_height))
            pygame.draw.rect(self.game_surface, (100, 150, 255), (dodge_x, dodge_y, int(dodge_bar_width * dodge_progress), dodge_bar_height))
            
            dodge_text = "DODGE"
            # Shadow
            shadow_surface = self.small_font.render(dodge_text, True, (0, 0, 0))
            self.game_surface.blit(shadow_surface, (dodge_x + dodge_bar_width + 4, dodge_y - 1))
            # Main text
            dodge_surface = self.small_font.render(dodge_text, True, (255, 255, 255))
            self.game_surface.blit(dodge_surface, (dodge_x + dodge_bar_width + 3, dodge_y - 2))
    
    def draw_game_over_screen(self):
        # Dark overlay with subtle gradient effect
        overlay = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
        overlay.set_alpha(220)
        overlay.fill((15, 15, 20))
        self.game_surface.blit(overlay, (0, 0))
        
        # Animated fade-in effect
        alpha = min(255, int(self.game_over_timer * 300))
        
        # Skull or death icon (simple pixel art)
        if alpha > 50:
            skull_x = GAME_WIDTH // 2
            skull_y = 30
            
            # Simple skull representation
            pygame.draw.circle(self.game_surface, (200, 200, 200), (skull_x, skull_y), 8)
            pygame.draw.circle(self.game_surface, BLACK, (skull_x - 3, skull_y - 2), 2)
            pygame.draw.circle(self.game_surface, BLACK, (skull_x + 3, skull_y - 2), 2)
            pygame.draw.rect(self.game_surface, BLACK, (skull_x - 1, skull_y + 2, 2, 4))
        
        # Main title with enhanced shadow effect
        title_font = pygame.font.Font(None, 48)
        title_text = title_font.render("GAME OVER", True, (220, 20, 60))
        title_shadow = title_font.render("GAME OVER", True, BLACK)
        
        title_rect = title_text.get_rect(center=(GAME_WIDTH//2, 70))
        shadow_rect = title_shadow.get_rect(center=(GAME_WIDTH//2 + 3, 73))
        
        title_text.set_alpha(alpha)
        title_shadow.set_alpha(alpha)
        
        self.game_surface.blit(title_shadow, shadow_rect)
        self.game_surface.blit(title_text, title_rect)
        
        # Stats box with enhanced design
        box_width = 300
        box_height = 160
        box_x = (GAME_WIDTH - box_width) // 2
        box_y = 100
        
        if alpha > 100:
            box_alpha = min(200, alpha - 100)
            
            # Gradient background for stats box
            box_surface = pygame.Surface((box_width, box_height))
            box_surface.set_alpha(box_alpha)
            box_surface.fill((25, 25, 35))
            self.game_surface.blit(box_surface, (box_x, box_y))
            
            # Multiple border layers for depth
            border_colors = [(80, 80, 90), (60, 60, 70), (40, 40, 50)]
            for i, border_color in enumerate(border_colors):
                pygame.draw.rect(self.game_surface, border_color, (box_x - i, box_y - i, box_width + 2*i, box_height + 2*i), 1)
            
            # Stats header with underline
            stats_font = pygame.font.Font(None, 28)
            header_text = stats_font.render("FINAL STATISTICS", True, (255, 215, 0))
            header_rect = header_text.get_rect(center=(GAME_WIDTH//2, box_y + 25))
            header_text.set_alpha(box_alpha)
            self.game_surface.blit(header_text, header_rect)
            
            # Underline for header
            pygame.draw.line(self.game_surface, (255, 215, 0), 
                           (header_rect.left, header_rect.bottom + 3), 
                           (header_rect.right, header_rect.bottom + 3), 2)
            
            # Individual stats with icons
            stats_y = box_y + 55
            stat_spacing = 22
            
            stats_data = [
                ("⏱", f"Survival Time: {self.survival_time:.1f}s", (150, 200, 255)),
                ("🏅", f"Highest Level: {self.current_level}", (255, 165, 0)),
                ("💀", f"Enemies Defeated: {self.enemies_killed}", (255, 100, 100)),
                ("💰", f"Money Collected: ${self.player.money}", (255, 215, 0)),
                ("🏆", f"Final Score: {self.final_score}", (100, 255, 100))
            ]
            
            for i, (icon, stat_text, color) in enumerate(stats_data):
                # Icon
                icon_surface = self.small_font.render(icon, True, color)
                icon_surface.set_alpha(box_alpha)
                icon_rect = (box_x + 20, stats_y + i * stat_spacing)
                self.game_surface.blit(icon_surface, icon_rect)
                
                # Stat text
                stat_surface = self.small_font.render(stat_text, True, WHITE)
                stat_surface.set_alpha(box_alpha)
                stat_rect = (box_x + 45, stats_y + i * stat_spacing)
                self.game_surface.blit(stat_surface, stat_rect)
        
        # Enhanced respawn button
        if self.game_over_timer > 1.5:
            button_width = 140
            button_height = 35
            button_x = GAME_WIDTH // 2 - button_width // 2
            button_y = GAME_HEIGHT - 70
            
            # Store button rect for click detection
            self.respawn_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
            
            # Check if mouse is hovering over button
            mouse_pos = pygame.mouse.get_pos()
            mouse_x = mouse_pos[0] // SCALE
            mouse_y = mouse_pos[1] // SCALE
            is_hovering = self.respawn_button_rect.collidepoint(mouse_x, mouse_y)
            
            # Button hover and pulse effect
            if is_hovering:
                pulse = abs(math.sin(self.game_over_timer * 8)) * 0.4 + 0.8
                button_color = (int(120 * pulse), int(180 * pulse), int(255))
                border_color = (255, 255, 255)
                border_width = 3
            else:
                pulse = abs(math.sin(self.game_over_timer * 4)) * 0.3 + 0.7
                button_color = (int(80 * pulse), int(130 * pulse), int(200 * pulse))
                border_color = (200, 200, 200)
                border_width = 2
            
            # Button shadow
            shadow_rect = pygame.Rect(button_x + 2, button_y + 2, button_width, button_height)
            pygame.draw.rect(self.game_surface, (20, 20, 20), shadow_rect, border_radius=8)
            
            # Main button
            button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
            pygame.draw.rect(self.game_surface, button_color, button_rect, border_radius=8)
            pygame.draw.rect(self.game_surface, border_color, button_rect, width=border_width, border_radius=8)
            
            # Button text with subtle glow effect when hovered
            button_font = pygame.font.Font(None, 26 if is_hovering else 24)
            button_text = button_font.render("RESPAWN", True, WHITE)
            button_text_rect = button_text.get_rect(center=button_rect.center)
            self.game_surface.blit(button_text, button_text_rect)
            
            # Add cursor pointer hint when hovering
            if is_hovering:
                # Small arrow indicators
                arrow_y = button_rect.centery
                pygame.draw.polygon(self.game_surface, WHITE, [
                    (button_rect.left - 8, arrow_y),
                    (button_rect.left - 12, arrow_y - 3),
                    (button_rect.left - 12, arrow_y + 3)
                ])
                pygame.draw.polygon(self.game_surface, WHITE, [
                    (button_rect.right + 8, arrow_y),
                    (button_rect.right + 12, arrow_y - 3),
                    (button_rect.right + 12, arrow_y + 3)
                ])
            
            # Smaller quit option
            quit_y = button_y + 45
            quit_text = self.small_font.render("Press ESC to Quit", True, (128, 128, 128))
            quit_rect = quit_text.get_rect(center=(GAME_WIDTH//2, quit_y))
            self.game_surface.blit(quit_text, quit_rect)
            
            # Additional instruction
            if self.game_over_timer > 3.0:
                instruction_text = self.small_font.render("Click button or press R to respawn", True, (180, 180, 180))
                instruction_rect = instruction_text.get_rect(center=(GAME_WIDTH//2, button_y - 15))
                self.game_surface.blit(instruction_text, instruction_rect)
    
    def draw(self):
        # Handle menu rendering
        if self.game_state != MenuState.GAME:
            self.menu_system.draw(self.game_surface)
        else:
            # Game rendering
            if self.background:
                # Draw sophisticated background first
                self.background.draw_background_layers(self.game_surface, self.camera)
            
            if not self.game_over and self.player:
                # Draw appropriate room
                if self.in_spawn_room and self.spawn_room:
                    self.spawn_room.draw(self.game_surface, self.camera, self)
                    # Draw teleporter if active
                    if self.multi_room_system:
                        self.multi_room_system.draw_teleporter(self.game_surface, self.camera)
                elif self.multi_room_system:
                    self.multi_room_system.get_current_room().draw(self.game_surface, self.camera)
                
                self.player.draw(self.game_surface, self.camera)
                self.draw_ui()
                
                # Draw objectives
                self.draw_objectives()
                
                # Draw hazard room hints
                if not self.in_spawn_room and self.multi_room_system:
                    current_room = self.multi_room_system.get_current_room()
                    if isinstance(current_room, HazardRoom):
                        self.draw_hazard_hints(current_room)
                
                # Room cleared notification
                if not self.in_spawn_room and hasattr(self, 'room_clear_timer') and self.room_clear_timer < 2.0:
                    overlay = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
                    overlay.set_alpha(120)
                    overlay.fill(BLACK)
                    self.game_surface.blit(overlay, (0, 0))
                    
                    clear_font = pygame.font.Font(None, 36)
                    clear_text = "ROOM CLEARED!"
                    clear_surface = clear_font.render(clear_text, True, (100, 255, 100))
                    clear_rect = clear_surface.get_rect(center=(GAME_WIDTH//2, GAME_HEIGHT//2 - 20))
                    self.game_surface.blit(clear_surface, clear_rect)
                    
                    progress_text = f"Level {self.current_level} - Room {self.rooms_cleared_this_level + 1}/{self.rooms_per_level}"
                    progress_surface = self.font.render(progress_text, True, WHITE)
                    progress_rect = progress_surface.get_rect(center=(GAME_WIDTH//2, GAME_HEIGHT//2 + 10))
                    self.game_surface.blit(progress_surface, progress_rect)
                    
                    if self.rooms_cleared_this_level + 1 >= self.rooms_per_level:
                        level_up_text = "LEVEL UP!"
                        level_up_surface = self.font.render(level_up_text, True, GOLD)
                        level_up_rect = level_up_surface.get_rect(center=(GAME_WIDTH//2, GAME_HEIGHT//2 + 30))
                        self.game_surface.blit(level_up_surface, level_up_rect)
                
                if self.paused:
                    overlay = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
                    overlay.set_alpha(128)
                    overlay.fill(BLACK)
                    self.game_surface.blit(overlay, (0, 0))
                    
                    pause_text = self.font.render("PAUSED - ESC to return to menu", True, WHITE)
                    text_rect = pause_text.get_rect(center=(GAME_WIDTH//2, GAME_HEIGHT//2))
                    self.game_surface.blit(pause_text, text_rect)
            
            else:
                self.draw_game_over_screen()
            
            # Draw shop overlay
            if self.shop:
                self.shop.draw(self.game_surface)
        
        # Calculate the scale to maintain aspect ratio while fitting the current window
        scale_x = self.current_screen_width / GAME_WIDTH
        scale_y = self.current_screen_height / GAME_HEIGHT
        scale = min(scale_x, scale_y)  # Use the smaller scale to maintain aspect ratio
        
        scaled_width = int(GAME_WIDTH * scale)
        scaled_height = int(GAME_HEIGHT * scale)
        
        # Center the scaled surface in the window
        offset_x = (self.current_screen_width - scaled_width) // 2
        offset_y = (self.current_screen_height - scaled_height) // 2
        
        # Fill the screen with black first (letterboxing)
        self.screen.fill(BLACK)
        
        # Scale and blit the game surface
        scaled_surface = pygame.transform.scale(self.game_surface, (scaled_width, scaled_height))
        self.screen.blit(scaled_surface, (offset_x, offset_y))
        pygame.display.flip()
    
    def run(self):
        last_time = time.time()
        
        while self.running:
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time
            
            dt = min(dt, 1/30)
            
            self.handle_events()
            self.update(dt)
            self.draw()
            
            self.clock.tick(60)
        
        pygame.quit()

    def update_objectives(self):
        """Update objective progress and check for completion"""
        if not self.objectives or not self.start_time:
            return
            
        current_time = time.time() - self.start_time
        
        for obj in self.objectives:
            if obj["completed"]:
                continue
                
            if obj["type"] == "rooms":
                obj["current"] = self.total_rooms_cleared
            elif obj["type"] == "kills":
                obj["current"] = self.enemies_killed
            elif obj["type"] == "level":
                obj["current"] = self.current_level
            elif obj["type"] == "time":
                obj["current"] = int(current_time)
            
            # Check if objective is completed
            if obj["current"] >= obj["target"] and not obj["completed"]:
                obj["completed"] = True
                if self.player:
                    self.player.money += obj["reward"]
                print(f"🎯 Objective Complete: {obj['name']} - Earned ${obj['reward']}!")
    
    def draw_objectives(self):
        """Draw objectives on the right side of screen"""
        if not self.objectives:
            return
            
        obj_x = GAME_WIDTH - 140
        obj_y = 60
        
        # Objectives title
        title_surface = self.small_font.render("OBJECTIVES", True, WHITE)
        self.game_surface.blit(title_surface, (obj_x, obj_y))
        
        # Draw each objective
        for i, obj in enumerate(self.objectives[:3]):  # Show only first 3 objectives
            y_pos = obj_y + 20 + i * 30
            
            # Objective name
            color = (100, 255, 100) if obj["completed"] else WHITE
            name_surface = self.small_font.render(obj["name"], True, color)
            self.game_surface.blit(name_surface, (obj_x, y_pos))
            
            # Progress
            progress_text = f"{obj['current']}/{obj['target']}"
            if obj["completed"]:
                progress_text = "COMPLETE!"
            progress_surface = self.small_font.render(progress_text, True, color)
            self.game_surface.blit(progress_surface, (obj_x, y_pos + 10))
            
            # Reward
            if not obj["completed"]:
                reward_text = f"${obj['reward']}"
                reward_surface = self.small_font.render(reward_text, True, GOLD)
                self.game_surface.blit(reward_surface, (obj_x + 80, y_pos + 10))
    
    def draw_hazard_hints(self, hazard_room):
        """Draw hints for hazard room mechanics"""
        hint_y = 10
        
        # Different hints based on hazard type
        if hasattr(hazard_room, 'ditches') and hazard_room.ditches:
            hint_text = "🕳️ DITCH CHALLENGE: Use DODGE ROLL (Space/RMB) to cross gaps!"
            hint_color = (255, 215, 0)
        elif hasattr(hazard_room, 'spikes') and hazard_room.spikes:
            hint_text = "⚡ SPIKE MAZE: Avoid the deadly spike traps!"
            hint_color = (255, 100, 100)
        elif hasattr(hazard_room, 'lava_tiles') and hazard_room.lava_tiles:
            hint_text = "🌋 LAVA CROSSING: Stay on stone bridges!"
            hint_color = (255, 140, 0)
        else:
            hint_text = "⚠️ HAZARD ROOM: Be careful!"
            hint_color = (200, 200, 200)
        
        # Enhanced hint background with better visibility
        hint_surface = self.small_font.render(hint_text, True, hint_color)
        hint_width = hint_surface.get_width()
        hint_height = hint_surface.get_height()
        
        bg_rect = (10, hint_y, hint_width + 10, hint_height + 4)
        pygame.draw.rect(self.game_surface, (0, 0, 0, 220), bg_rect)  # Darker background
        pygame.draw.rect(self.game_surface, hint_color, bg_rect, 3)  # Thicker border
        
        # Draw hint text with shadow
        # Shadow
        shadow_surface = self.small_font.render(hint_text, True, (0, 0, 0))
        self.game_surface.blit(shadow_surface, (16, hint_y + 3))
        # Main text
        self.game_surface.blit(hint_surface, (15, hint_y + 2))
        
        # Enhanced progress indicator with shadow
        if not hazard_room.challenge_complete:
            progress_text = "Reach the end platform to complete the challenge!"
            # Shadow
            shadow_surface = self.small_font.render(progress_text, True, (0, 0, 0))
            self.game_surface.blit(shadow_surface, (16, hint_y + 28))
            # Main text
            progress_surface = self.small_font.render(progress_text, True, (255, 255, 255))
            progress_bg_rect = (10, hint_y + 25, progress_surface.get_width() + 10, progress_surface.get_height() + 4)
            pygame.draw.rect(self.game_surface, (0, 0, 0, 200), progress_bg_rect)  # Darker background
            pygame.draw.rect(self.game_surface, (200, 200, 200), progress_bg_rect, 2)  # Brighter border
            self.game_surface.blit(progress_surface, (15, hint_y + 27))

class MultiRoomSystem:
    def __init__(self, level=1):
        self.level = level
        self.rooms = {}
        self.current_room_id = "room_1"
        self.doors = {}
        self.room_connections = {}
        self.rooms_cleared = set()
        # Set total rooms based on level
        if self.level == 1:
            self.total_rooms = 3  # 2 combat + 1 hazard + boss
        elif self.level == 2:
            self.total_rooms = 4  # 3 combat + 1 hazard + boss
        elif self.level == 3:
            self.total_rooms = 5  # 4 combat + 1 hazard + boss
        else:  # Level 4+
            self.total_rooms = 6  # 5 combat + 1 hazard + boss
        self.teleporter_active = False
        self.enemy_waves = {}
        self.current_wave = {}
        
        self.generate_room_layout()
    
    def generate_room_layout(self):
        """Generate connected rooms with doors for each level"""
        # Each level has its own interconnected room layout
        if self.level == 1:
            room_configs = [
                {"id": "room_1", "pos": (0, 0), "connections": ["room_2"], "type": "combat"},
                {"id": "room_2", "pos": (1, 0), "connections": ["room_1", "hazard_room"], "type": "combat"},
                {"id": "hazard_room", "pos": (2, 0), "connections": ["room_2", "boss_room"], "type": "hazard"},
                {"id": "boss_room", "pos": (3, 0), "connections": ["hazard_room"], "type": "boss"}
            ]
        elif self.level == 2:
            room_configs = [
                {"id": "room_1", "pos": (0, 0), "connections": ["room_2"], "type": "combat"},
                {"id": "room_2", "pos": (1, 0), "connections": ["room_1", "room_3"], "type": "combat"},
                {"id": "room_3", "pos": (2, 0), "connections": ["room_2", "hazard_room"], "type": "combat"},
                {"id": "hazard_room", "pos": (3, 0), "connections": ["room_3", "boss_room"], "type": "hazard"},
                {"id": "boss_room", "pos": (4, 0), "connections": ["hazard_room"], "type": "boss"}
            ]
        elif self.level == 3:
            room_configs = [
                {"id": "room_1", "pos": (0, 0), "connections": ["room_2"], "type": "combat"},
                {"id": "room_2", "pos": (1, 0), "connections": ["room_1", "room_3"], "type": "combat"},
                {"id": "room_3", "pos": (2, 0), "connections": ["room_2", "hazard_room"], "type": "combat"},
                {"id": "hazard_room", "pos": (3, 0), "connections": ["room_3", "room_4"], "type": "hazard"},
                {"id": "room_4", "pos": (4, 0), "connections": ["hazard_room", "boss_room"], "type": "combat"},
                {"id": "boss_room", "pos": (5, 0), "connections": ["room_4"], "type": "boss"}
            ]
        else:  # Level 4+
            room_configs = [
                {"id": "room_1", "pos": (0, 0), "connections": ["room_2"], "type": "combat"},
                {"id": "room_2", "pos": (1, 0), "connections": ["room_1", "room_3"], "type": "combat"},
                {"id": "room_3", "pos": (2, 0), "connections": ["room_2", "hazard_room"], "type": "combat"},
                {"id": "hazard_room", "pos": (3, 0), "connections": ["room_3", "room_4"], "type": "hazard"},
                {"id": "room_4", "pos": (4, 0), "connections": ["hazard_room", "room_5"], "type": "combat"},
                {"id": "room_5", "pos": (5, 0), "connections": ["room_4", "boss_room"], "type": "combat"},
                {"id": "boss_room", "pos": (6, 0), "connections": ["room_5"], "type": "boss"}
            ]
        
        for config in room_configs:
            if config["type"] == "boss":
                # Boss room is special
                self.rooms[config["id"]] = BossRoom(level=self.level)
            elif config["type"] == "hazard":
                # Hazard room with environmental challenges
                self.rooms[config["id"]] = HazardRoom(level=self.level)
                print(f"🎯 Generated Hazard Room for Level {self.level}")
            else:
                # Regular combat room
                self.rooms[config["id"]] = Room(level=self.level)
            
            self.room_connections[config["id"]] = config["connections"]
            
            # Setup enemy waves for combat rooms only
            if config["type"] == "combat":
                self.enemy_waves[config["id"]] = self.generate_enemy_waves(config["id"])
                self.current_wave[config["id"]] = 0
        
        # Generate doors between connected rooms
        self.generate_doors()
    
    def generate_enemy_waves(self, room_id):
        """Generate multiple waves of enemies for each room"""
        waves = []
        base_enemies = 3 + self.level
        
        for wave in range(2):  # Reduced to 2 waves per room
            wave_enemies = base_enemies + wave * 2
            enemy_types = ["basic", "aggressive", "sniper", "rusher"]
            
            # Difficulty scales with wave and level
            if wave == 0:  # First wave - easier
                weights = [60, 20, 15, 5]
            else:  # Second wave - harder
                weights = [30, 35, 25, 10]
            
            wave_data = {
                "enemy_count": wave_enemies,
                "enemy_types": enemy_types,
                "weights": weights,
                "spawned": False,
                "cleared": False
            }
            waves.append(wave_data)
        
        return waves
    
    def generate_doors(self):
        """Create sliding doors between connected rooms"""
        # Generate doors based on level layout
        door_positions = {}
        
        if self.level == 1:
            door_positions = {
                ("room_1", "room_2"): (24 * 16, 10 * 16, "horizontal"),  # Right side of room_1
                ("room_2", "hazard_room"): (24 * 16, 10 * 16, "horizontal"),  # Right side of room_2
                ("hazard_room", "boss_room"): (24 * 16, 10 * 16, "horizontal"),  # Right side of hazard_room
            }
        elif self.level == 2:
            door_positions = {
                ("room_1", "room_2"): (24 * 16, 10 * 16, "horizontal"),  # Right side of room_1
                ("room_2", "room_3"): (24 * 16, 10 * 16, "horizontal"),  # Right side of room_2
                ("room_3", "hazard_room"): (24 * 16, 10 * 16, "horizontal"),  # Right side of room_3
                ("hazard_room", "boss_room"): (24 * 16, 10 * 16, "horizontal"),  # Right side of hazard_room
            }
        elif self.level == 3:
            door_positions = {
                ("room_1", "room_2"): (24 * 16, 10 * 16, "horizontal"),  # Right side of room_1
                ("room_2", "room_3"): (24 * 16, 10 * 16, "horizontal"),  # Right side of room_2
                ("room_3", "hazard_room"): (24 * 16, 10 * 16, "horizontal"),  # Right side of room_3
                ("hazard_room", "room_4"): (24 * 16, 10 * 16, "horizontal"),  # Right side of hazard_room
                ("room_4", "boss_room"): (24 * 16, 10 * 16, "horizontal"),  # Right side of room_4
            }
        else:  # Level 4+
            door_positions = {
                ("room_1", "room_2"): (24 * 16, 10 * 16, "horizontal"),  # Right side of room_1
                ("room_2", "room_3"): (24 * 16, 10 * 16, "horizontal"),  # Right side of room_2
                ("room_3", "hazard_room"): (24 * 16, 10 * 16, "horizontal"),  # Right side of room_3
                ("hazard_room", "room_4"): (24 * 16, 10 * 16, "horizontal"),  # Right side of hazard_room
                ("room_4", "room_5"): (24 * 16, 10 * 16, "horizontal"),  # Right side of room_4
                ("room_5", "boss_room"): (24 * 16, 10 * 16, "horizontal"),  # Right side of room_5
            }
        
        for (room1, room2), (x, y, direction) in door_positions.items():
            door_id = f"{room1}_{room2}"
            self.doors[door_id] = Door(x, y, direction)
    
    def get_current_room(self):
        return self.rooms[self.current_room_id]
    
    def update(self, dt, player):
        current_room = self.get_current_room()
        current_room.update(dt, player)
        
        # Update doors
        for door in self.doors.values():
            player_nearby = door.pos.distance_to(player.pos) < 50 if hasattr(door, 'pos') else False
            door.update(dt, player_nearby)
        
        # Handle room-specific logic
        current_room = self.get_current_room()
        if isinstance(current_room, HazardRoom):
            # Check hazard room completion
            if current_room.challenge_complete and self.current_room_id not in self.rooms_cleared:
                self.rooms_cleared.add(self.current_room_id)
                print(f"✅ {self.current_room_id} challenge completed!")
        elif self.current_room_id != "boss_room":
            # Handle enemy waves for combat rooms
            self.handle_enemy_waves()
        
        # Check room transitions
        self.check_room_transitions(player)
        
        # Check teleporter activation
        if len(self.rooms_cleared) >= self.total_rooms and not self.teleporter_active:
            self.teleporter_active = True
            print("🌟 All rooms cleared! Teleporter to boss room activated!")
    
    def handle_enemy_waves(self):
        current_room = self.get_current_room()
        room_waves = self.enemy_waves.get(self.current_room_id, [])
        current_wave_idx = self.current_wave.get(self.current_room_id, 0)
        
        if current_wave_idx < len(room_waves):
            wave = room_waves[current_wave_idx]
            
            # Spawn wave if not already spawned and room is empty
            if not wave["spawned"] and len(current_room.enemies) == 0:
                self.spawn_enemy_wave(current_room, wave)
                wave["spawned"] = True
                print(f"🌊 Wave {current_wave_idx + 1} spawned in {self.current_room_id}!")
            
            # Check if wave is cleared
            if wave["spawned"] and len(current_room.enemies) == 0 and not wave["cleared"]:
                wave["cleared"] = True
                self.current_wave[self.current_room_id] += 1
                
                if self.current_wave[self.current_room_id] >= len(room_waves):
                    # All waves cleared in this room
                    self.rooms_cleared.add(self.current_room_id)
                    print(f"✅ {self.current_room_id} completely cleared!")
                else:
                    print(f"🌊 Wave {current_wave_idx + 1} cleared! Next wave incoming...")
    
    def spawn_enemy_wave(self, room, wave_data):
        """Spawn a wave of enemies"""
        for _ in range(wave_data["enemy_count"]):
            attempts = 0
            while attempts < 50:
                x = random.randint(3, room.width - 4) * 16
                y = random.randint(3, room.height - 4) * 16
                
                tile_x, tile_y = x // 16, y // 16
                if (tile_x, tile_y) in room.floor_tiles:
                    # Check distance from other enemies
                    too_close = False
                    for existing_enemy in room.enemies:
                        if Vector2(x, y).distance_to(existing_enemy.pos) < 32:
                            too_close = True
                            break
                    
                    if not too_close:
                        enemy_type = random.choices(wave_data["enemy_types"], weights=wave_data["weights"])[0]
                        room.enemies.append(Enemy(x, y, enemy_type, self.level))
                        break
                attempts += 1
    
    def check_room_transitions(self, player):
        """Check if player should transition between rooms"""
        for door_id, door in self.doors.items():
            if door.can_pass_through():
                # Check if player is touching the door
                door_rect = door.get_collision_rect()
                if door_rect is None:  # Door is open
                    # Get door position for transition check
                    if hasattr(door, 'x') and hasattr(door, 'y'):
                        door_center_x = door.x + door.width // 2
                        door_center_y = door.y + door.height // 2
                        
                        if Vector2(door_center_x, door_center_y).distance_to(player.pos) < 20:
                            # Determine target room
                            room1, room2 = door_id.split('_', 1)
                            if room2.startswith('room'):
                                room2 = room2.split('_', 1)[1]
                                room2 = f"room_{room2}"
                            
                            target_room = room2 if self.current_room_id == room1 else room1
                            
                            if target_room in self.rooms:
                                self.transition_to_room(target_room, player)
    
    def transition_to_room(self, target_room_id, player):
        """Transition player to a different room"""
        if target_room_id != self.current_room_id:
            self.current_room_id = target_room_id
            
            # Position player at appropriate entrance
            if target_room_id == "boss_room":
                player.pos = Vector2(240, 320)  # Bottom center of smaller boss room
            elif target_room_id == "hazard_room":
                player.pos = Vector2(64, 48)  # Start platform in hazard room
            else:
                player.pos = Vector2(200, 200)  # Center-ish of regular rooms
            
            print(f"🚪 Entered {target_room_id}")
    
    def draw_teleporter(self, screen, camera):
        """Draw teleporter station when active"""
        if not self.teleporter_active:
            return
        
        # Teleporter position (center of smaller spawn room)
        teleporter_x = 120
        teleporter_y = 96
        screen_x = teleporter_x - camera.x
        screen_y = teleporter_y - camera.y
        
        if (-50 <= screen_x <= GAME_WIDTH + 50 and -50 <= screen_y <= GAME_HEIGHT + 50):
            # Teleporter base
            pygame.draw.circle(screen, MYSTICAL_BLUE, (int(screen_x), int(screen_y)), 20)
            pygame.draw.circle(screen, (MYSTICAL_BLUE[0] + 30, MYSTICAL_BLUE[1] + 50, MYSTICAL_BLUE[2] + 80), 
                             (int(screen_x), int(screen_y)), 20, 3)
            
            # Animated energy effect
            energy_pulse = math.sin(time.time() * 4) * 0.3 + 0.7
            inner_radius = int(15 * energy_pulse)
            pygame.draw.circle(screen, (100, 200, 255), (int(screen_x), int(screen_y)), inner_radius)
            
            # Teleporter text
            font = pygame.font.Font(None, 16)
            text = font.render("BOSS TELEPORTER", True, WHITE)
            text_rect = text.get_rect(center=(screen_x, screen_y - 35))
            screen.blit(text, text_rect)

class HazardRoom(Room):
    def __init__(self, level=1):
        super().__init__(width=25, height=20, level=level)
        self.ditches = set()
        self.bridges = set()
        self.spikes = set()
        self.lava_tiles = set()
        self.moving_platforms = []
        self.challenge_complete = False
        self.entrance_door = None
        self.exit_door = None
        self.generate_hazard_room()
        
    def generate_hazard_room(self):
        """Generate a room with environmental hazards"""
        # Clear default room generation
        self.walls.clear()
        self.floor_tiles.clear()
        
        # Create walls around perimeter
        for x in range(self.width):
            self.walls.add((x, 0))
            self.walls.add((x, self.height - 1))
        for y in range(self.height):
            self.walls.add((0, y))
            self.walls.add((self.width - 1, y))
        
        # Create safe starting platform
        for x in range(2, 6):
            for y in range(2, 5):
                self.floor_tiles.add((x, y))
        
        # Create ending platform
        for x in range(self.width - 6, self.width - 2):
            for y in range(self.height - 5, self.height - 2):
                self.floor_tiles.add((x, y))
        
        # Generate different types of hazards based on level
        if self.level <= 3:
            self.generate_ditch_challenge()
        elif self.level <= 6:
            self.generate_spike_maze()
        else:
            self.generate_lava_crossing()
        
        # Add some enemies for extra challenge
        self.spawn_hazard_enemies()
    
    def generate_ditch_challenge(self):
        """Generate ditches that can only be crossed by dodge rolling"""
        # Create a series of ditches with small platforms
        current_x = 6
        while current_x < self.width - 8:
            # Ditch width (can be crossed by dodge roll)
            ditch_width = random.randint(3, 5)
            
            # Create vertical ditch
            for x in range(current_x, min(current_x + ditch_width, self.width - 2)):
                for y in range(2, self.height - 2):
                    self.ditches.add((x, y))
            
            # Small platform after ditch
            platform_start = current_x + ditch_width
            platform_width = random.randint(2, 4)
            
            for x in range(platform_start, min(platform_start + platform_width, self.width - 2)):
                for y in range(3, self.height - 3):
                    self.floor_tiles.add((x, y))
            
            current_x = platform_start + platform_width + 1
        
        print("🕳️ Ditch Challenge: Use dodge roll to cross the gaps!")
    
    def generate_spike_maze(self):
        """Generate a maze with spike traps"""
        # Create floor tiles in a maze pattern
        for x in range(2, self.width - 2):
            for y in range(2, self.height - 2):
                if (x + y) % 3 != 0:  # Create some pattern
                    self.floor_tiles.add((x, y))
        
        # Add spike traps
        for x in range(4, self.width - 4, 3):
            for y in range(4, self.height - 4, 3):
                if (x, y) in self.floor_tiles:
                    self.spikes.add((x, y))
                    self.floor_tiles.remove((x, y))
        
        print("⚡ Spike Maze: Avoid the deadly spikes!")
    
    def generate_lava_crossing(self):
        """Generate lava tiles with moving platforms"""
        # Fill middle area with lava
        for x in range(4, self.width - 4):
            for y in range(4, self.height - 4):
                self.lava_tiles.add((x, y))
        
        # Create some safe stone bridges
        bridge_y = self.height // 2
        for x in range(6, self.width - 6, 4):
            for bx in range(x, min(x + 2, self.width - 2)):
                self.bridges.add((bx, bridge_y))
                if (bx, bridge_y) in self.lava_tiles:
                    self.lava_tiles.remove((bx, bridge_y))
                self.floor_tiles.add((bx, bridge_y))
        
        print("🌋 Lava Crossing: Stay on the stone bridges!")
    
    def spawn_hazard_enemies(self):
        """Spawn a few enemies for extra challenge"""
        # Only spawn 1-2 enemies in hazard rooms
        for _ in range(random.randint(1, 2)):
            attempts = 0
            while attempts < 30:
                x = random.randint(3, self.width - 4) * 16
                y = random.randint(3, self.height - 4) * 16
                
                tile_x, tile_y = x // 16, y // 16
                if (tile_x, tile_y) in self.floor_tiles:
                    # Make sure it's not on the starting platform
                    if tile_x < 6 or tile_x > self.width - 6:
                        continue
                    
                    enemy_type = random.choice(["sniper", "basic"])  # Easier enemies
                    self.enemies.append(Enemy(x, y, enemy_type, max(1, self.level - 1)))
                    break
                attempts += 1
    
    def update(self, dt, player):
        super().update(dt, player)
        
        # Check if player completed the challenge (reached end platform)
        if not self.challenge_complete:
            end_area_x = self.width - 6
            end_area_y = self.height - 5
            
            player_tile_x = int(player.pos.x // 16)
            player_tile_y = int(player.pos.y // 16)
            
            if (player_tile_x >= end_area_x and player_tile_y >= end_area_y and 
                len(self.enemies) == 0):
                self.challenge_complete = True
                print("🎉 Hazard Challenge Complete! Well done!")
    
    def check_hazard_damage(self, player):
        """Check if player is taking hazard damage"""
        player_tile_x = int(player.pos.x // 16)
        player_tile_y = int(player.pos.y // 16)
        
        # Only take damage if not invulnerable and not dodging
        if player.invulnerable or player.is_dodging:
            return False
        
        # Check ditch damage (instant death if you fall in)
        if (player_tile_x, player_tile_y) in self.ditches:
            print("💀 You fell into a ditch!")
            player.health = 0  # Instant death
            return True
        
        # Check spike damage
        if (player_tile_x, player_tile_y) in self.spikes:
            print("⚡ Spike trap!")
            player.take_damage(20)
            return True
        
        # Check lava damage
        if (player_tile_x, player_tile_y) in self.lava_tiles:
            print("🔥 Lava burns!")
            player.take_damage(15)
            return True
        
        return False
    
    def draw(self, screen, camera):
        # Draw basic room structure first
        super().draw(screen, camera)
        
        # Draw ditches (black voids)
        for x, y in self.ditches:
            screen_x = x * 16 - camera.x
            screen_y = y * 16 - camera.y
            pygame.draw.rect(screen, BLACK, (screen_x, screen_y, 16, 16))
            # Add some depth with dark border
            pygame.draw.rect(screen, (10, 10, 10), (screen_x, screen_y, 16, 16), 2)
        
        # Draw spikes (gray triangular patterns)
        for x, y in self.spikes:
            screen_x = x * 16 - camera.x
            screen_y = y * 16 - camera.y
            
            # Draw spike base
            pygame.draw.rect(screen, (80, 80, 80), (screen_x, screen_y, 16, 16))
            
            # Draw spike points
            for i in range(3):
                spike_x = screen_x + 2 + i * 5
                spike_points = [
                    (spike_x, screen_y + 12),
                    (spike_x + 2, screen_y + 4),
                    (spike_x + 4, screen_y + 12)
                ]
                pygame.draw.polygon(screen, (120, 120, 120), spike_points)
        
        # Draw lava (animated red/orange)
        lava_pulse = abs(math.sin(time.time() * 4)) * 0.3 + 0.7
        lava_color = (int(255 * lava_pulse), int(69 * lava_pulse), 0)
        
        for x, y in self.lava_tiles:
            screen_x = x * 16 - camera.x
            screen_y = y * 16 - camera.y
            pygame.draw.rect(screen, lava_color, (screen_x, screen_y, 16, 16))
            # Add bubbling effect
            if random.random() < 0.1:
                bubble_x = screen_x + random.randint(2, 14)
                bubble_y = screen_y + random.randint(2, 14)
                pygame.draw.circle(screen, (255, 140, 0), (bubble_x, bubble_y), 2)
        
        # Draw stone bridges
        for x, y in self.bridges:
            screen_x = x * 16 - camera.x
            screen_y = y * 16 - camera.y
            pygame.draw.rect(screen, (100, 100, 100), (screen_x, screen_y, 16, 16))
            pygame.draw.rect(screen, (120, 120, 120), (screen_x, screen_y, 16, 16), 2)

class BossRoom(Room):
    def __init__(self, level=1):
        super().__init__(width=30, height=25, level=level)
        self.boss = None
        self.boss_spawned = False
        
    def spawn_boss(self):
        """Spawn the boss enemy"""
        if not self.boss_spawned:
            # Clear any regular enemies
            self.enemies.clear()
            
            # Spawn boss in center
            boss_x = self.width // 2 * 16
            boss_y = self.height // 2 * 16
            self.boss = Boss(boss_x, boss_y, self.level)
            self.enemies.append(self.boss)
            self.boss_spawned = True
            print("💀 BOSS FIGHT BEGINS!")

class Boss(Enemy):
    def __init__(self, x, y, level=1):
        super().__init__(x, y, "basic", level)
        self.size = 20  # Much larger
        self.health = 200 + level * 50  # Much more health
        self.max_health = self.health
        self.damage = 15 + level * 3
        self.contact_damage = 25 + level * 5
        self.speed = 40  # Slower but more dangerous
        self.fire_rate = 2.0  # Faster firing
        self.detection_range = 300
        
        # Boss-specific attributes
        self.phase = 1
        self.special_attack_timer = 0.0
        self.special_attack_cooldown = 5.0
    
    def update(self, dt, player_pos, walls):
        super().update(dt, player_pos, walls)
        
        # Boss special attacks
        self.special_attack_timer += dt
        if self.special_attack_timer >= self.special_attack_cooldown:
            self.special_attack_timer = 0.0
            return self.special_attack(player_pos)
        return []
    
    def special_attack(self, player_pos):
        """Boss special attack - burst of bullets"""
        bullets = []
        for i in range(8):  # 8-way burst
            angle = (i / 8) * 2 * math.pi
            bullet = Bullet(self.pos.x, self.pos.y, angle, 120, self.damage, BULLET_RED, 4)
            bullets.append(bullet)
        print("💥 Boss special attack!")
        return bullets
    
    def draw(self, screen, camera):
        screen_x = int(self.pos.x - camera.x)
        screen_y = int(self.pos.y - camera.y)
        
        # Boss appearance - much larger and more menacing
        # Main body
        pygame.draw.circle(screen, (150, 0, 0), (screen_x, screen_y), self.size)
        pygame.draw.circle(screen, (200, 50, 50), (screen_x, screen_y), self.size, 3)
        
        # Eyes
        pygame.draw.circle(screen, (255, 0, 0), (screen_x - 8, screen_y - 5), 3)
        pygame.draw.circle(screen, (255, 0, 0), (screen_x + 8, screen_y - 5), 3)
        
        # Crown/spikes
        for i in range(6):
            angle = (i / 6) * 2 * math.pi
            spike_x = screen_x + math.cos(angle) * (self.size + 5)
            spike_y = screen_y + math.sin(angle) * (self.size + 5)
            pygame.draw.line(screen, (100, 0, 0), (screen_x, screen_y), (spike_x, spike_y), 3)
        
        # Health bar - larger for boss
        bar_width = 40
        bar_height = 6
        health_ratio = self.health / self.max_health
        
        pygame.draw.rect(screen, DARK_GRAY, (screen_x - bar_width//2, screen_y - self.size - 15, bar_width, bar_height))
        pygame.draw.rect(screen, HEALTH_RED, (screen_x - bar_width//2, screen_y - self.size - 15, int(bar_width * health_ratio), bar_height))
        pygame.draw.rect(screen, WHITE, (screen_x - bar_width//2, screen_y - self.size - 15, bar_width, bar_height), 1)

def main():
    game = GungeonGame()
    game.run()

if __name__ == "__main__":
    main() 