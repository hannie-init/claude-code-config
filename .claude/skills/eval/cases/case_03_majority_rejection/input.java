package com.example.harness.notification;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

/**
 * Sends push notifications to eligible users for a given event.
 * Eligibility is determined by user preferences stored in the database.
 */
@Service
public class NotificationDispatchService {

    @Autowired
    private UserPreferenceRepository preferenceRepository;

    @Autowired
    private NotificationSender notificationSender;

    @Autowired
    private NotificationLogRepository logRepository;

    @Transactional
    public DispatchResult dispatch(NotificationEvent event) {
        List<UserPreference> prefs = preferenceRepository.findByEventType(event.getType());

        List<Long> targetUserIds = prefs.stream()
                .filter(UserPreference::isEnabled)
                .map(UserPreference::getUserId)
                .collect(Collectors.toList());

        if (targetUserIds.isEmpty()) {
            return DispatchResult.noTargets();
        }

        int sent = 0;
        int failed = 0;
        for (Long userId : targetUserIds) {
            try {
                notificationSender.send(userId, event.buildPayload());
                logRepository.save(NotificationLog.success(userId, event.getId()));
                sent++;
            } catch (NotificationDeliveryException e) {
                logRepository.save(NotificationLog.failure(userId, event.getId(), e.getMessage()));
                failed++;
            }
        }

        return new DispatchResult(sent, failed);
    }

    @Transactional(readOnly = true)
    public List<NotificationLog> getRecentLogs(Long userId, int limit) {
        return logRepository.findTopByUserIdOrderByCreatedAtDesc(userId, limit);
    }

    // Visible for testing
    boolean isEligible(UserPreference pref) {
        return pref != null && pref.isEnabled() && pref.getChannel() != null;
    }
}
