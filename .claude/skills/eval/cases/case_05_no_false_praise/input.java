package com.example.harness.product;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Optional;

/**
 * Provides paginated product search with an in-memory cache layer.
 */
@Service
@Transactional(readOnly = true)
public class ProductSearchService {

    private static final int MAX_PAGE_SIZE = 50;

    private final ProductRepository productRepository;
    private final SearchCacheService searchCacheService;
    private final ProductMapper productMapper;

    public ProductSearchService(ProductRepository productRepository,
                                SearchCacheService searchCacheService,
                                ProductMapper productMapper) {
        this.productRepository = productRepository;
        this.searchCacheService = searchCacheService;
        this.productMapper = productMapper;
    }

    public Page<ProductDto> search(SearchCriteria criteria, Pageable pageable) {
        Pageable capped = capPageSize(pageable);
        String cacheKey = criteria.toCacheKey(capped);

        Page<ProductDto> cached = searchCacheService.get(cacheKey);
        if (cached != null) {
            return cached;
        }

        Page<Product> products = productRepository.findByCriteria(criteria, capped);
        Page<ProductDto> result = products.map(productMapper::toDto);

        searchCacheService.put(cacheKey, result);
        return result;
    }

    public Optional<ProductDto> findById(Long id) {
        return productRepository.findById(id)
                .map(productMapper::toDto);
    }

    public Page<ProductDto> findByCategory(Long categoryId, Pageable pageable) {
        Pageable capped = capPageSize(pageable);
        return productRepository.findByCategoryId(categoryId, capped)
                .map(productMapper::toDto);
    }

    private Pageable capPageSize(Pageable pageable) {
        if (pageable.getPageSize() <= MAX_PAGE_SIZE) {
            return pageable;
        }
        return PageRequest.of(pageable.getPageNumber(), MAX_PAGE_SIZE, pageable.getSort());
    }
}
