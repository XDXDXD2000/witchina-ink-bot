from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

class Database:
    def __init__(self):
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Подключение к Supabase установлено!")

    def get_services(self) -> List[Dict[str, Any]]:
        response = self.supabase.table('services').select('*').execute()
        return response.data

    def get_free_slots(self, date_str: str) -> List[str]:
        from config import WORK_START_HOUR, WORK_END_HOUR, SLOT_DURATION_MINUTES
        
        start_dt = datetime.strptime(date_str, "%Y-%m-%d")
        end_dt = start_dt.replace(hour=WORK_END_HOUR, minute=0)
        
        all_slots = []
        current = start_dt.replace(hour=WORK_START_HOUR, minute=0)
        while current < end_dt:
            if current > datetime.now() + timedelta(hours=0):
                all_slots.append(current.strftime("%H:%M"))
            current += timedelta(minutes=SLOT_DURATION_MINUTES)
        
        if not all_slots:
            return []
        
        response = self.supabase.table('appointments')\
            .select('slot_start')\
            .eq('status', 'booked')\
            .execute()
        
        booked_slots = []
        for row in response.data:
            if row["slot_start"].startswith(date_str):
                booked_slots.append(row["slot_start"].split("T")[1][:5])
        
        return [slot for slot in all_slots if slot not in booked_slots]

    def book_appointment(self, user_id: int, username: str, phone: str,
                         service_id: int, slot_start: str, description: str = "",
                         secret_used: str = None, discount_percent: int = 0) -> Optional[int]:
        try:
            existing = self.supabase.table('appointments')\
                .select('id')\
                .eq('slot_start', slot_start)\
                .eq('status', 'booked')\
                .execute()
            
            if existing.data:
                return None
            
            response = self.supabase.table('appointments').insert({
                "user_id": user_id,
                "username": username,
                "phone": phone,
                "service_id": service_id,
                "slot_start": slot_start,
                "description": description,
                "secret_used": secret_used,
                "discount_percent": discount_percent
            }).execute()
            return response.data[0]['id'] if response.data else None
        except Exception as e:
            print(f"Ошибка записи: {e}")
            return None

    def get_user_appointments(self, user_id: int) -> List[Dict[str, Any]]:
        response = self.supabase.table('appointments')\
            .select('*, service_id, services(name, price)')\
            .eq('user_id', user_id)\
            .eq('status', 'booked')\
            .execute()
        
        for row in response.data:
            if 'services' in row:
                row['service_name'] = row['services']['name']
                row['price'] = row['services']['price']
                del row['services']
        return response.data

    def get_all_appointments(self) -> List[Dict[str, Any]]:
        response = self.supabase.table('appointments')\
            .select('*, service_id, services(name)')\
            .eq('status', 'booked')\
            .order('slot_start')\
            .execute()
        
        for row in response.data:
            if 'services' in row:
                row['service_name'] = row['services']['name']
                del row['services']
        return response.data

    def get_appointment_by_id(self, appointment_id: int) -> Optional[Dict[str, Any]]:
        response = self.supabase.table('appointments')\
            .select('*, service_id, services(name)')\
            .eq('id', appointment_id)\
            .execute()
        
        if response.data:
            row = response.data[0]
            if 'services' in row:
                row['service_name'] = row['services']['name']
                del row['services']
            return row
        return None

    def cancel_appointment(self, appointment_id: int, user_id: int) -> bool:
        response = self.supabase.table('appointments')\
            .update({"status": "cancelled"})\
            .eq('id', appointment_id)\
            .eq('user_id', user_id)\
            .execute()
        return len(response.data) > 0

    def get_all_users(self) -> List[Dict[str, Any]]:
        response = self.supabase.table('appointments')\
            .select('user_id, username')\
            .execute()
        users = {}
        for row in response.data:
            users[row['user_id']] = row
        return list(users.values())

    def add_review(self, user_id: int, username: str, rating: int, text: str) -> int:
        response = self.supabase.table('reviews').insert({
            "user_id": user_id,
            "username": username,
            "rating": rating,
            "text": text,
            "status": "pending"
        }).execute()
        return response.data[0]['id'] if response.data else None

    def get_approved_reviews(self, limit: int = 20) -> List[Dict[str, Any]]:
        response = self.supabase.table('reviews')\
            .select('*')\
            .eq('status', 'approved')\
            .order('created_at', desc=True)\
            .limit(limit)\
            .execute()
        return response.data

    def get_pending_reviews(self) -> List[Dict[str, Any]]:
        response = self.supabase.table('reviews')\
            .select('*')\
            .eq('status', 'pending')\
            .order('created_at')\
            .execute()
        return response.data

    def moderate_review(self, review_id: int, action: str) -> bool:
        if action not in ['approved', 'rejected']:
            return False
        response = self.supabase.table('reviews')\
            .update({"status": action})\
            .eq('id', review_id)\
            .execute()
        return len(response.data) > 0

    def check_user_reviewed(self, user_id: int) -> bool:
        response = self.supabase.table('reviews')\
            .select('id')\
            .eq('user_id', user_id)\
            .neq('status', 'rejected')\
            .execute()
        return len(response.data) > 0

    def get_appointments_for_reminder(self, hours_before: int) -> List[Dict[str, Any]]:
        now = datetime.now()
        target_time = now + timedelta(hours=hours_before)
        target_time_str = target_time.strftime("%Y-%m-%dT%H:00:00")
        
        response = self.supabase.table('appointments')\
            .select('*')\
            .eq('status', 'booked')\
            .eq('reminder_sent', False)\
            .execute()
        
        result = []
        for row in response.data:
            service_response = self.supabase.table('services')\
                .select('name')\
                .eq('id', row['service_id'])\
                .execute()
            service_name = service_response.data[0]['name'] if service_response.data else "Неизвестно"
            
            row['service_name'] = service_name
            
            if row['slot_start'].startswith(target_time_str[:16]):
                result.append(row)
        return result

    def mark_reminder_sent(self, appointment_id: int) -> None:
        self.supabase.table('appointments')\
            .update({"reminder_sent": True})\
            .eq('id', appointment_id)\
            .execute()

    def cleanup_old_appointments(self, days: int = 30) -> int:
        return 0

db = Database()