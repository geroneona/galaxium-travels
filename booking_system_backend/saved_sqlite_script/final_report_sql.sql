select * from users;
select * from bookings;
select * from flights;
select * from discounts;

select u.name, u.email, 
d.applied_discounted_price_per_infant_count, 
ifnull(d.infant_count,0) as infant_count,
b.booking_time, 
b.booking_id, b.status
from bookings b 
left join users u 
on b.user_id = u.user_id
left join discounts d 
on b.booking_id = d.booking_id
left join flights f
on b.flight_id = f.flight_id ;

select u.name, u.email, 
CASE 
	WHEN d.applied_discounted_price_per_infant_count IS NULL
	THEN f.price
	ELSE d.applied_discounted_price_per_infant_count
END AS total_price, 
ifnull(d.infant_count,0) as infant_count,
b.booking_time, 
b.booking_id, b.status
from bookings b 
left join users u 
on b.user_id = u.user_id
left join discounts d 
on b.booking_id = d.booking_id
left join flights f
on b.flight_id = f.flight_id ;