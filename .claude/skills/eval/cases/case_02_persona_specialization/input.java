package com.example.harness.order;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;

@Service
@Transactional
public class OrderSummaryService {

    @Autowired
    private OrderRepository orderRepository;

    @Autowired
    private OrderItemRepository orderItemRepository;

    @Autowired
    private EmailService emailService;

    @Autowired
    private PdfExportService pdfExportService;

    public List<OrderSummaryDto> generateMonthlySummary(Long customerId, int year, int month) {
        List<Order> orders = orderRepository.findByCustomerIdAndYearMonth(customerId, year, month);
        List<OrderSummaryDto> summaries = new ArrayList<>();

        for (Order order : orders) {
            List<OrderItem> items = orderItemRepository.findByOrderId(order.getId());

            double total = 0;
            for (OrderItem item : items) {
                total += item.getUnitPrice() * item.getQuantity();
            }

            summaries.add(new OrderSummaryDto(order.getId(), order.getCreatedAt(), items, total));
        }

        byte[] pdfBytes = pdfExportService.renderSummary(summaries);
        emailService.sendMonthlySummary(customerId, pdfBytes);

        return summaries;
    }

    public OrderSummaryDto getOrderDetail(Long orderId) {
        Order order = orderRepository.findById(orderId)
                .orElseThrow(() -> new IllegalArgumentException("Order not found: " + orderId));

        List<OrderItem> items = orderItemRepository.findByOrderId(orderId);
        double total = 0;
        for (OrderItem item : items) {
            total += item.getUnitPrice() * item.getQuantity();
        }

        return new OrderSummaryDto(order.getId(), order.getCreatedAt(), items, total);
    }

    public List<OrderSummaryDto> getPendingOrdersSummary(Long customerId) {
        List<Order> pending = orderRepository.findByCustomerIdAndStatus(customerId, OrderStatus.PENDING);
        List<OrderSummaryDto> results = new ArrayList<>();

        for (Order order : pending) {
            List<OrderItem> items = orderItemRepository.findByOrderId(order.getId());
            double total = items.stream()
                    .mapToDouble(i -> i.getUnitPrice() * i.getQuantity())
                    .sum();
            results.add(new OrderSummaryDto(order.getId(), order.getCreatedAt(), items, total));
        }

        return results;
    }
}
