import json
import os
from datetime import datetime, timedelta

class HotelBookingSystem:
    def __init__(self, filename='bookings.json'):
        self.filename = filename
        self.bookings = self.load_bookings()
        # define rooms: price per night and total count
        self.rooms = {
            'single': {'price': 2000, 'total': 10},
            'double': {'price': 2500, 'total': 8},
            'suite':  {'price': 3000, 'total': 5}
        }

    # ---------- persistence ----------
    def load_bookings(self):
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []
        return []

    def save_bookings(self):
        with open(self.filename, 'w') as f:
            json.dump(self.bookings, f, indent=2, default=str)

    # ---------- helpers ----------
    def generate_booking_id(self):
        # find highest numeric suffix in existing IDs BK0001 etc.
        max_n = 0
        for b in self.bookings:
            bid = b.get('booking_id', '')
            if bid.startswith('BK'):
                try:
                    n = int(bid[2:])
                    if n > max_n:
                        max_n = n
                except ValueError:
                    pass
        return f"BK{max_n + 1:04d}"

    def parse_date(self, date_str):
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except Exception:
            return None

    def calculate_nights(self, check_in, check_out):
        date_in = self.parse_date(check_in)
        date_out = self.parse_date(check_out)
        if date_in is None or date_out is None:
            return None
        return (date_out - date_in).days

    def dates_overlap(self, start1, end1, start2, end2):
        # treat end as exclusive (check-out day not occupied)
        return (start1 < end2) and (start2 < end1)

    # ---------- availability ----------
    def booked_count_for_range(self, room_type, check_in, check_out):
        """Count confirmed bookings of room_type that overlap the given range."""
        date_in = self.parse_date(check_in)
        date_out = self.parse_date(check_out)
        if date_in is None or date_out is None:
            return None
        count = 0
        for b in self.bookings:
            if b.get('room_type') != room_type:
                continue
            if b.get('status') != 'confirmed':
                continue
            b_in = self.parse_date(b['check_in'])
            b_out = self.parse_date(b['check_out'])
            if self.dates_overlap(date_in, date_out, b_in, b_out):
                count += 1
        return count

    def available_rooms_for_range(self, room_type, check_in, check_out):
        """Return number of available rooms of given type for the date range."""
        if room_type not in self.rooms:
            return None
        booked = self.booked_count_for_range(room_type, check_in, check_out)
        if booked is None:
            return None
        return max(0, self.rooms[room_type]['total'] - booked)

    # ---------- CRUD ----------
    def create_booking(self, guest_name, email, phone, room_type, check_in, check_out, guests):
        if room_type not in self.rooms:
            return None, "Invalid room type"

        nights = self.calculate_nights(check_in, check_out)
        if nights is None:
            return None, "Invalid date format. Use YYYY-MM-DD"
        if nights <= 0:
            return None, "Check-out must be after check-in"

        available = self.available_rooms_for_range(room_type, check_in, check_out)
        if available is None:
            return None, "Error calculating availability"
        if available <= 0:
            return None, f"No {room_type} rooms available for those dates"

        total_price = self.rooms[room_type]['price'] * nights

        booking = {
            'booking_id': self.generate_booking_id(),
            'guest_name': guest_name,
            'email': email,
            'phone': phone,
            'room_type': room_type,
            'check_in': check_in,
            'check_out': check_out,
            'guests': guests,
            'nights': nights,
            'total_price': total_price,
            'status': 'confirmed',
            'created_at': datetime.now().isoformat()
        }

        self.bookings.append(booking)
        self.save_bookings()
        return booking, "Booking created successfully"

    def get_booking(self, booking_id):
        for booking in self.bookings:
            if booking['booking_id'] == booking_id:
                return booking
        return None

    def get_all_bookings(self):
        return self.bookings

    def cancel_booking(self, booking_id):
        for booking in self.bookings:
            if booking['booking_id'] == booking_id:
                if booking['status'] == 'cancelled':
                    return booking  # already cancelled
                booking['status'] = 'cancelled'
                booking['cancelled_at'] = datetime.now().isoformat()
                self.save_bookings()
                return booking
        return None

    def search_bookings(self, query):
        results = []
        query_lower = query.lower()
        for booking in self.bookings:
            if (query_lower in booking['guest_name'].lower() or
                query_lower in booking['email'].lower() or
                query_lower in booking['booking_id'].lower()):
                results.append(booking)
        return results

    def get_available_rooms(self):
        """Return availability for today (simple helper)."""
        today = datetime.now().date().isoformat()
        tomorrow = (datetime.now().date() + timedelta(days=1)).isoformat()
        availability = {}
        for room_type in self.rooms:
            availability[room_type] = self.available_rooms_for_range(room_type, today, tomorrow)
        return availability

# ---------- CLI ----------
if __name__ == '__main__':
    system = HotelBookingSystem()

    while True:
        print("\n=== Hotel Booking Management System ===")
        print("1. Create Booking")
        print("2. View All Bookings")
        print("3. Search Booking")
        print("4. Cancel Booking")
        print("5. View Available Rooms (for a date range)")
        print("6. Exit")

        choice = input("\nEnter choice: ").strip()

        if choice == '1':
            print("\n--- New Booking ---")
            guest_name = input("Guest Name: ").strip()
            email = input("Email: ").strip()
            phone = input("Phone: ").strip()

            print("\nRoom Types:")
            for room_type, info in system.rooms.items():
                print(f"  {room_type.capitalize()}: ₹{info['price']}/night (total {info['total']})")

            room_type = input("Room Type: ").lower().strip()
            check_in = input("Check-in (YYYY-MM-DD): ").strip()
            check_out = input("Check-out (YYYY-MM-DD): ").strip()
            try:
                guests = int(input("Number of Guests: ").strip())
            except ValueError:
                guests = 1

            booking, message = system.create_booking(guest_name, email, phone, room_type, check_in, check_out, guests)
            if booking:
                print(f"\n✓ {message}")
                print(f"Booking ID: {booking['booking_id']}")
                print(f"Total: ₹{booking['total_price']} for {booking['nights']} nights")
            else:
                print(f"\n✗ {message}")

        elif choice == '2':
            bookings = system.get_all_bookings()
            if bookings:
                print("\n--- All Bookings ---")
                for b in bookings:
                    print(f"\nID: {b['booking_id']} | Guest: {b['guest_name']} | Room: {b['room_type'].capitalize()}")
                    print(f"Check-in: {b['check_in']} | Check-out: {b['check_out']} | Status: {b['status']}")
                    print(f"Total: ₹{b['total_price']} ({b['nights']} nights)")
            else:
                print("\nNo bookings found.")

        elif choice == '3':
            query = input("Search (Booking ID/Name/Email): ").strip()
            results = system.search_bookings(query)
            if results:
                print("\n--- Search Results ---")
                for b in results:
                    print(f"\nID: {b['booking_id']} | Guest: {b['guest_name']} | Room: {b['room_type'].capitalize()}")
                    print(f"Check-in: {b['check_in']} | Check-out: {b['check_out']} | Status: {b['status']}")
            else:
                print("\nNo matches found.")

        elif choice == '4':
            booking_id = input("Booking ID to cancel: ").strip()
            booking = system.cancel_booking(booking_id)
            if booking:
                print(f"\n✓ Booking {booking_id} cancelled successfully")
            else:
                print("\n✗ Booking not found")

        elif choice == '5':
            print("\nEnter date range to check availability.")
            check_in = input("Check-in (YYYY-MM-DD): ").strip()
            check_out = input("Check-out (YYYY-MM-DD): ").strip()
            print("\n--- Availability ---")
            for room_type in system.rooms:
                avail = system.available_rooms_for_range(room_type, check_in, check_out)
                if avail is None:
                    print("Invalid date(s) provided.")
                    break
                print(f"{room_type.capitalize()}: {avail} available out of {system.rooms[room_type]['total']}")
        elif choice == '6':
            print("\nThank you for using Hotel Booking System!")
            break
        else:
            print("\nInvalid choice.")
