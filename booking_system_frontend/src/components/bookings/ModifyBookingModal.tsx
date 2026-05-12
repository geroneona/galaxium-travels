import { useState, useEffect } from 'react';
import type { Booking, Flight } from '../../types';
import { Modal, Button, LoadingSpinner } from '../common';
import { Plane, Calendar, Clock, DollarSign, ArrowRight } from 'lucide-react';
import { formatCurrency, formatDate, calculateDuration } from '../../utils/formatters';
import { modifyBooking, getFlights, isErrorResponse } from '../../services/api';
import { useUser } from '../../hooks/useUser';
import toast from 'react-hot-toast';
import { motion } from 'framer-motion';

interface ModifyBookingModalProps {
  isOpen: boolean;
  onClose: () => void;
  booking: Booking | null;
  currentFlight: Flight | null;
  onSuccess: () => void;
}

export const ModifyBookingModal = ({
  isOpen,
  onClose,
  booking,
  currentFlight,
  onSuccess,
}: ModifyBookingModalProps) => {
  const { user } = useUser();
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingFlights, setIsLoadingFlights] = useState(false);
  const [availableFlights, setAvailableFlights] = useState<Flight[]>([]);
  const [selectedFlight, setSelectedFlight] = useState<Flight | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadAvailableFlights();
    }
  }, [isOpen]);

  const loadAvailableFlights = async () => {
    setIsLoadingFlights(true);
    try {
      const flights = await getFlights();
      // Filter out the current flight and flights with no seats
      const filtered = flights.filter(
        (f) => f.flight_id !== booking?.flight_id && f.seats_available > 0
      );
      setAvailableFlights(filtered);
    } catch (error: any) {
      toast.error('Failed to load available flights');
      console.error(error);
    } finally {
      setIsLoadingFlights(false);
    }
  };

  const handleConfirmModify = async () => {
    if (!user || !booking || !selectedFlight) {
      toast.error('Please select a flight');
      return;
    }

    setIsLoading(true);

    try {
      const result = await modifyBooking({
        booking_id: booking.booking_id,
        new_flight_id: selectedFlight.flight_id,
        user_id: user.user_id,
      });

      if (isErrorResponse(result)) {
        toast.error(result.details || result.error);
        return;
      }

      toast.success('Booking modified successfully!');
      onSuccess();
      onClose();
      setSelectedFlight(null);
    } catch (error: any) {
      toast.error(error.details || error.error || 'Failed to modify booking');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    setSelectedFlight(null);
    onClose();
  };

  if (!booking || !currentFlight) return null;

  const priceDifference = selectedFlight
    ? selectedFlight.price - currentFlight.price
    : 0;

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Modify Your Booking"
      size="lg"
    >
      <div className="space-y-6">
        {/* Current Flight */}
        <div>
          <h4 className="text-sm font-semibold text-star-white/60 mb-2">
            Current Flight
          </h4>
          <div className="glass-card p-4 bg-white/5">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 rounded-lg bg-cosmic-gradient">
                <Plane className="text-white" size={20} />
              </div>
              <div>
                <h3 className="text-lg font-bold text-star-white">
                  {currentFlight.origin} → {currentFlight.destination}
                </h3>
                <p className="text-xs text-star-white/60">
                  Flight #{currentFlight.flight_id}
                </p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-star-white/60">Departure</p>
                <p className="text-star-white">{formatDate(currentFlight.departure_time)}</p>
              </div>
              <div>
                <p className="text-star-white/60">Price</p>
                <p className="text-star-white font-semibold">
                  {formatCurrency(currentFlight.price)}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Available Flights */}
        <div>
          <h4 className="text-sm font-semibold text-star-white/60 mb-2">
            Select New Flight
          </h4>
          {isLoadingFlights ? (
            <LoadingSpinner size="sm" text="Loading flights..." />
          ) : availableFlights.length === 0 ? (
            <div className="glass-card p-6 text-center">
              <p className="text-star-white/60">No alternative flights available</p>
            </div>
          ) : (
            <div className="space-y-3 max-h-96 overflow-y-auto pr-2">
              {availableFlights.map((flight) => (
                <motion.div
                  key={flight.flight_id}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <button
                    onClick={() => setSelectedFlight(flight)}
                    className={`w-full glass-card p-4 text-left transition-all ${
                      selectedFlight?.flight_id === flight.flight_id
                        ? 'bg-cosmic-gradient border-2 border-cosmic-purple'
                        : 'bg-white/5 hover:bg-white/10'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <h3 className="text-base font-bold text-star-white">
                          {flight.origin} → {flight.destination}
                        </h3>
                        <p className="text-xs text-star-white/60">
                          Flight #{flight.flight_id}
                        </p>
                      </div>
                      <span className="text-lg font-bold text-star-white">
                        {formatCurrency(flight.price)}
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div>
                        <p className="text-star-white/60">Departure</p>
                        <p className="text-star-white">{formatDate(flight.departure_time)}</p>
                      </div>
                      <div>
                        <p className="text-star-white/60">Duration</p>
                        <p className="text-star-white">
                          {calculateDuration(flight.departure_time, flight.arrival_time)}
                        </p>
                      </div>
                      <div>
                        <p className="text-star-white/60">Seats</p>
                        <p className="text-star-white">{flight.seats_available} available</p>
                      </div>
                    </div>
                  </button>
                </motion.div>
              ))}
            </div>
          )}
        </div>

        {/* Price Difference */}
        {selectedFlight && (
          <div className="glass-card p-4 bg-cosmic-gradient">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <DollarSign className="text-white" size={20} />
                <span className="text-white font-semibold">Price Difference</span>
              </div>
              <span
                className={`text-xl font-bold ${
                  priceDifference > 0
                    ? 'text-red-300'
                    : priceDifference < 0
                    ? 'text-green-300'
                    : 'text-white'
                }`}
              >
                {priceDifference > 0 ? '+' : ''}
                {formatCurrency(Math.abs(priceDifference))}
              </span>
            </div>
            {priceDifference !== 0 && (
              <p className="text-xs text-white/70 mt-2">
                {priceDifference > 0
                  ? 'Additional payment required'
                  : 'Credit will be applied'}
              </p>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <Button
            variant="secondary"
            onClick={handleClose}
            disabled={isLoading}
            className="flex-1"
          >
            Cancel
          </Button>
          <Button
            onClick={handleConfirmModify}
            isLoading={isLoading}
            disabled={!selectedFlight}
            className="flex-1"
          >
            Confirm Modification
          </Button>
        </div>

        <p className="text-xs text-star-white/60 text-center">
          Your original booking will be updated with the new flight details
        </p>
      </div>
    </Modal>
  );
};

// Made with Bob