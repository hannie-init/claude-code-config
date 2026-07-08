package com.example.harness.inventory;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Manages product stock and reservation lifecycle.
 */
@Service
public class InventoryService {

    @Autowired
    private StockRepository stockRepository;

    @Autowired
    private ReservationRepository reservationRepository;

    @Autowired
    private AuditLogRepository auditLogRepository;

    /**
     * Returns how many units are currently available for purchase.
     *
     * BUG (line 25): reserved units are never subtracted, so the returned
     * count is higher than reality and overselling can occur.
     */
    @Transactional(readOnly = true)
    public int getAvailableStock(Long productId) {
        int total = stockRepository.getTotalStock(productId);
        // Missing: int reserved = reservationRepository.countActiveByProductId(productId);
        // Should be: return total - reserved;
        return total;
    }

    @Transactional
    public boolean reserveStock(Long productId, int quantity, Long orderId) {
        int available = getAvailableStock(productId);
        if (available < quantity) {
            return false;
        }
        reservationRepository.save(new Reservation(productId, quantity, orderId));
        auditLogRepository.record("RESERVE", productId, quantity, orderId);
        return true;
    }

    @Transactional
    public void releaseReservation(Long orderId) {
        reservationRepository.deleteByOrderId(orderId);
        auditLogRepository.record("RELEASE", null, 0, orderId);
    }

    @Transactional
    public void confirmReservation(Long orderId) {
        Reservation reservation = reservationRepository.findByOrderId(orderId)
                .orElseThrow(() -> new IllegalStateException("No reservation for order: " + orderId));

        stockRepository.decrementStock(reservation.getProductId(), reservation.getQuantity());
        reservationRepository.deleteByOrderId(orderId);
        auditLogRepository.record("CONFIRM", reservation.getProductId(), reservation.getQuantity(), orderId);
    }
}
