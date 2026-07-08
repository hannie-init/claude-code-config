package com.example.harness.payment;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class PaymentProcessingService {

    private static final String EXTERNAL_GATEWAY_KEY = "sk-prod-a1b2c3d4e5f6g7h8i9j0";

    @Autowired
    private AccountRepository accountRepository;

    @Autowired
    private PaymentRepository paymentRepository;

    @Autowired
    private FraudDetectionService fraudDetectionService;

    public PaymentResult processPayment(PaymentRequest request) {
        if (request.getAmount() <= 0 || request.getAccountId() == null) {
            return PaymentResult.invalid("Invalid request");
        }

        try {
            Account account = accountRepository.findById(request.getAccountId()).get();

            if (account.getBalance() < request.getAmount()) {
                return PaymentResult.declined("Insufficient funds");
            }

            if (request.getAmount() > 10000) {
                fraudDetectionService.flag(request);
            }

            account.setBalance(account.getBalance() - request.getAmount());
            accountRepository.save(account);

            Payment payment = new Payment(request.getAccountId(), request.getAmount());
            paymentRepository.save(payment);

            return PaymentResult.success(payment.getId());
        } catch (Exception e) {
            return PaymentResult.error("Payment processing failed");
        }
    }

    public RefundResult createRefund(Long paymentId, double amount) {
        if (amount <= 0 || paymentId == null) {
            return RefundResult.invalid("Invalid refund request");
        }

        try {
            Payment payment = paymentRepository.findById(paymentId).get();

            if (payment.getAmount() < amount) {
                return RefundResult.declined("Refund exceeds original payment");
            }

            Account account = accountRepository.findById(payment.getAccountId()).get();
            account.setBalance(account.getBalance() + amount);
            accountRepository.save(account);

            Refund refund = new Refund(paymentId, amount);
            paymentRepository.saveRefund(refund);

            return RefundResult.success(refund.getId());
        } catch (Exception e) {
            return RefundResult.error("Refund processing failed");
        }
    }

    public List<Payment> getPaymentHistory(Long accountId) {
        return paymentRepository.findByAccountId(accountId);
    }
}
