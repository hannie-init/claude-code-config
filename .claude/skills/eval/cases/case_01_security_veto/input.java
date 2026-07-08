package com.example.harness.user;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;

@Service
public class UserSearchService {

    @Autowired
    private JdbcTemplate jdbcTemplate;

    public List<Map<String, Object>> searchByUsername(String username) {
        String sql = "SELECT id, username, email, role FROM users WHERE username = '" + username + "'";
        return jdbcTemplate.queryForList(sql);
    }

    public List<Map<String, Object>> searchByEmail(String email) {
        String query = "SELECT id, username, email FROM users"
                + " WHERE email = '" + email + "' AND active = 1";
        return jdbcTemplate.queryForList(query);
    }

    public Map<String, Object> findById(Long id) {
        String sql = "SELECT id, username, email, role, created_at FROM users WHERE id = " + id;
        return jdbcTemplate.queryForMap(sql);
    }

    public List<Map<String, Object>> searchByRole(String role, String department) {
        String sql = "SELECT u.id, u.username, u.email, d.name AS dept_name"
                + " FROM users u JOIN departments d ON u.dept_id = d.id"
                + " WHERE u.role = '" + role + "' AND d.name = '" + department + "'";
        return jdbcTemplate.queryForList(sql);
    }

    public boolean existsByUsername(String username) {
        String sql = "SELECT COUNT(*) FROM users WHERE username = '" + username + "'";
        Integer count = jdbcTemplate.queryForObject(sql, Integer.class);
        return count != null && count > 0;
    }
}
