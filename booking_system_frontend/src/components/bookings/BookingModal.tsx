import { useState } from 'react';
import type { Flight } from '../../types';
import { Modal, Button } from '../common';
import { Plane, Calendar, Clock, DollarSign, Baby } from 'lucide-react';
import { formatCurrency, formatDate, calculateDuration } from '../../utils/formatters';
import { bookFlight, isErrorResponse } from '../../services/api';
import { useUser } from '../../hooks/useUser';
import toast from 'react-hot-toast';

interface BookingModalProps {
  isOpen: boolean;
  onClose: () => void;
  flight: Flight | null;
  onSuccess: () => void;
}

export const BookingModal = ({ isOpen, onClose, flight, onSuccess }: BookingModalProps) => {
  const { user } = useUser();
  const [isLoading, setIsLoading] = useState(false);
  const [infantCount, setInfantCount] = useState(0);

  if (!flight) return null;

  // Calculate total price including infant discount
  const calculateTotalPrice = () => {
    const basePrice = flight.price;
    if (infantCount > 1) {
      // 25% discount per infant for multiple infants
      const infantDiscount = basePrice * 0.25 * (infantCount-1);
      return basePrice + infantDiscount;
    }
    return basePrice; // No charge for single infant
  };

  const totalPrice = calculateTotalPrice();


  const handleConfirmBooking = async () => {
    if (!user) {
      toast.error('Please sign in to book a flight');
      return;
    }

    setIsLoading(true);

    try {
      const result = await bookFlight({
        user_id: user.user_id,
        name: user.name,
        flight_id: flight.flight_id,
        infant_count: infantCount,
      });

      if (isErrorResponse(result)) {
        toast.error(result.details || result.error);
        return;
      }

      toast.success('Flight booked successfully!');
      onSuccess();
      onClose();
    } catch (error: any) {
      toast.error(error.details || error.error || 'Failed to book flight');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Confirm Your Booking"
      size="md"
    >
      <div className="space-y-6">
        {/* Flight Summary */}
        <div className="glass-card p-4 bg-white/5">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-lg bg-cosmic-gradient">
              <Plane className="text-white" size={24} />
            </div>
            <div>
              <h3 className="text-xl font-bold text-star-white">
                {flight.origin} → {flight.destination}
              </h3>
              <p className="text-sm text-star-white/60">
                Flight #{flight.flight_id}
              </p>
            </div>
          </div>

          <div className="space-y-3">
            {/* Departure */}
            <div className="flex items-start gap-3">
              <Calendar className="text-cosmic-purple mt-1" size={20} />
              <div>
                <p className="text-xs text-star-white/60">Departure</p>
                <p className="text-star-white font-medium">
                  {formatDate(flight.departure_time)}
                </p>
              </div>
            </div>

            {/* Arrival */}
            <div className="flex items-start gap-3">
              <Calendar className="text-cosmic-purple mt-1" size={20} />
              <div>
                <p className="text-xs text-star-white/60">Arrival</p>
                <p className="text-star-white font-medium">
                  {formatDate(flight.arrival_time)}
                </p>
              </div>
            </div>

            {/* Duration */}
            <div className="flex items-start gap-3">
              <Clock className="text-cosmic-purple mt-1" size={20} />
              <div>
                <p className="text-xs text-star-white/60">Duration</p>
                <p className="text-star-white font-medium">
                  {calculateDuration(flight.departure_time, flight.arrival_time)}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Passenger Info */}
        {user && (
          <div className="glass-card p-4 bg-white/5">
            <h4 className="text-sm font-semibold text-star-white mb-2">
              Passenger Information
            </h4>
            <p className="text-star-white">{user.name}</p>
            <p className="text-star-white/60 text-sm">{user.email}</p>
          </div>
        )}

        {/* Infant Selection */}
        <div className="glass-card p-4 bg-white/5">
          <div className="flex items-center gap-2 mb-3">
            <Baby className="text-cosmic-purple" size={20} />
            <h4 className="text-sm font-semibold text-star-white">
              Traveling with Infants?
            </h4>
          </div>
          <p className="text-xs text-star-white/60 mb-3">
            Infants (under 2 years) can sit on your lap and don't require a separate seat. However, for more than one infant, a 75% discount applies per infant.
          </p>
          <div className="flex items-center gap-4">
            <label className="text-star-white text-sm">Number of infants:</label>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setInfantCount(Math.max(0, infantCount - 1))}
                disabled={infantCount === 0 || isLoading}
                className="w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed text-star-white font-bold transition-colors"
              >
                -
              </button>
              <span className="w-12 text-center text-star-white font-semibold">
                {infantCount}
              </span>
              <button
                type="button"
                onClick={() => setInfantCount(Math.min(8, infantCount + 1))}
                disabled={infantCount === 8 || isLoading}
                className="w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed text-star-white font-bold transition-colors"
              >
                +
              </button>
            </div>
          </div>
          {infantCount > 0 && (
            <p className="text-xs text-cosmic-purple mt-2">
              {infantCount} infant{infantCount > 1 ? 's' : ''} selected 
              {infantCount > 1 
                ? ` (75% discount per infant: +${formatCurrency(flight.price * 0.25 * (infantCount-1))})`
                : ' (no additional charge)'
              }
            </p>
          )}
        </div>

        {/* Price */}
        <div className="flex items-center justify-between p-4 glass-card bg-cosmic-gradient">
          <div className="flex items-center gap-2">
            <DollarSign className="text-white" size={24} />
            <span className="text-white font-semibold">Total Price</span>
          </div>
          <div className="text-right">
            {infantCount > 1 && (
              <div className="text-sm text-white/80 line-through">
                {formatCurrency(flight.price)}
              </div>
            )}
            <span className="text-2xl font-bold text-white">
              {formatCurrency(totalPrice)}
            </span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <Button
            variant="secondary"
            onClick={onClose}
            disabled={isLoading}
            className="flex-1"
          >
            Cancel
          </Button>
          <Button
            onClick={handleConfirmBooking}
            isLoading={isLoading}
            className="flex-1"
          >
            Confirm Booking
          </Button>
        </div>

        <p className="text-xs text-star-white/60 text-center">
          By confirming, you agree to our terms and conditions
        </p>
      </div>
    </Modal>
  );
};

// Made with Bob
