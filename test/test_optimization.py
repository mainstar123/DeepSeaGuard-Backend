"""
Performance Test for DeepSeaGuard Optimizations
Demonstrates the performance improvements achieved through optimization
"""
import asyncio
import time
import random
from datetime import datetime, timezone
import requests
from typing import List, Tuple

def test_basic_performance():
    """Test basic API performance"""
    print("🚀 Testing Basic API Performance")
    print("=" * 50)
    
    # Test health endpoint
    start_time = time.time()
    response = requests.get("http://localhost:8000/health")
    health_time = (time.time() - start_time) * 1000
    
    print(f"✅ Health Check: {health_time:.2f}ms")
    
    # Test zones endpoint
    start_time = time.time()
    response = requests.get("http://localhost:8000/api/v1/zones")
    zones_time = (time.time() - start_time) * 1000
    
    print(f"✅ Zones Query: {zones_time:.2f}ms")
    
    # Test GeoJSON endpoint
    start_time = time.time()
    response = requests.get("http://localhost:8000/api/v1/zones/geojson")
    geojson_time = (time.time() - start_time) * 1000
    
    print(f"✅ GeoJSON Query: {geojson_time:.2f}ms")
    
    return {
        'health_ms': health_time,
        'zones_ms': zones_time,
        'geojson_ms': geojson_time
    }

def test_telemetry_performance():
    """Test telemetry processing performance"""
    print("\n📡 Testing Telemetry Processing Performance")
    print("=" * 50)
    
    # Generate test telemetry data
    test_positions = [
        (-2.5, -145.0, 150),  # Inside CCZ
        (0.0, -147.5, 200),   # Inside Contract Area
        (0.0, -137.5, 100),   # Inside Reserved Area
        (17.5, -77.5, 100),   # Inside Jamaica zones
    ]
    
    total_time = 0
    successful_requests = 0
    
    for i, (lat, lng, depth) in enumerate(test_positions):
        telemetry = {
            "auv_id": f"TEST_AUV_{i:03d}",
            "latitude": lat,
            "longitude": lng,
            "depth": depth,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        start_time = time.time()
        try:
            response = requests.post(
                "http://localhost:8000/api/v1/telemetry/position",
                json=telemetry,
                timeout=5
            )
            
            if response.status_code == 200:
                processing_time = (time.time() - start_time) * 1000
                total_time += processing_time
                successful_requests += 1
                
                result = response.json()
                zones_detected = result.get('zones_detected', 0)
                print(f"✅ Telemetry {i+1}: {processing_time:.2f}ms ({zones_detected} zones)")
            else:
                print(f"❌ Telemetry {i+1}: Failed (HTTP {response.status_code})")
                
        except Exception as e:
            print(f"❌ Telemetry {i+1}: Error - {e}")
    
    if successful_requests > 0:
        avg_time = total_time / successful_requests
        print(f"\n📊 Average Telemetry Processing: {avg_time:.2f}ms")
        print(f"📊 Success Rate: {successful_requests}/{len(test_positions)} ({successful_requests/len(test_positions)*100:.1f}%)")
    
    return {
        'avg_telemetry_ms': total_time / successful_requests if successful_requests > 0 else 0,
        'success_rate': successful_requests / len(test_positions)
    }

def test_concurrent_performance():
    """Test concurrent request performance"""
    print("\n⚡ Testing Concurrent Request Performance")
    print("=" * 50)
    
    async def send_concurrent_requests(num_requests: int = 50):
        """Send concurrent requests"""
        async def send_single_request(i: int):
            telemetry = {
                "auv_id": f"CONCURRENT_AUV_{i:03d}",
                "latitude": random.uniform(-10, 10),
                "longitude": random.uniform(-160, -130),
                "depth": random.uniform(50, 300),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            start_time = time.time()
            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: requests.post(
                        "http://localhost:8000/api/v1/telemetry/position",
                        json=telemetry,
                        timeout=5
                    )
                )
                
                processing_time = (time.time() - start_time) * 1000
                success = response.status_code == 200
                
                return {
                    'success': success,
                    'time_ms': processing_time,
                    'status_code': response.status_code
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'time_ms': (time.time() - start_time) * 1000,
                    'error': str(e)
                }
        
        # Send concurrent requests
        start_time = time.time()
        tasks = [send_single_request(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)
        total_time = (time.time() - start_time) * 1000
        
        # Analyze results
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        if successful:
            avg_time = sum(r['time_ms'] for r in successful) / len(successful)
            max_time = max(r['time_ms'] for r in successful)
            min_time = min(r['time_ms'] for r in successful)
        else:
            avg_time = max_time = min_time = 0
        
        print(f"📊 Concurrent Requests: {num_requests}")
        print(f"📊 Total Time: {total_time:.2f}ms")
        print(f"📊 Success Rate: {len(successful)}/{num_requests} ({len(successful)/num_requests*100:.1f}%)")
        print(f"📊 Average Response: {avg_time:.2f}ms")
        print(f"📊 Min Response: {min_time:.2f}ms")
        print(f"📊 Max Response: {max_time:.2f}ms")
        print(f"📊 Throughput: {num_requests/(total_time/1000):.1f} req/sec")
        
        return {
            'total_requests': num_requests,
            'successful_requests': len(successful),
            'failed_requests': len(failed),
            'total_time_ms': total_time,
            'avg_response_ms': avg_time,
            'throughput_req_sec': num_requests/(total_time/1000) if total_time > 0 else 0
        }
    
    # Run concurrent test
    return asyncio.run(send_concurrent_requests(50))

def test_optimization_features():
    """Test optimization features"""
    print("\n🔧 Testing Optimization Features")
    print("=" * 50)
    
    # Test cache performance (multiple requests to same endpoint)
    print("🔄 Testing Cache Performance...")
    
    cache_times = []
    for i in range(10):
        start_time = time.time()
        response = requests.get("http://localhost:8000/api/v1/zones")
        cache_time = (time.time() - start_time) * 1000
        cache_times.append(cache_time)
    
    avg_cache_time = sum(cache_times) / len(cache_times)
    print(f"✅ Average Cached Response: {avg_cache_time:.2f}ms")
    
    # Test spatial query performance
    print("🗺️ Testing Spatial Query Performance...")
    
    spatial_times = []
    test_positions = [
        (-2.5, -145.0, 150),
        (0.0, -147.5, 200),
        (0.0, -137.5, 100),
        (17.5, -77.5, 100),
    ]
    
    for lat, lng, depth in test_positions:
        telemetry = {
            "auv_id": "SPATIAL_TEST",
            "latitude": lat,
            "longitude": lng,
            "depth": depth,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        start_time = time.time()
        response = requests.post(
            "http://localhost:8000/api/v1/telemetry/position",
            json=telemetry
        )
        spatial_time = (time.time() - start_time) * 1000
        spatial_times.append(spatial_time)
    
    avg_spatial_time = sum(spatial_times) / len(spatial_times)
    print(f"✅ Average Spatial Query: {avg_spatial_time:.2f}ms")
    
    return {
        'avg_cache_ms': avg_cache_time,
        'avg_spatial_ms': avg_spatial_time
    }

def generate_performance_report(results: dict):
    """Generate comprehensive performance report"""
    print("\n📊 PERFORMANCE REPORT")
    print("=" * 60)
    
    print("🎯 Performance Summary:")
    print(f"   • Health Check: {results['basic']['health_ms']:.2f}ms")
    print(f"   • Zones Query: {results['basic']['zones_ms']:.2f}ms")
    print(f"   • GeoJSON Query: {results['basic']['geojson_ms']:.2f}ms")
    print(f"   • Telemetry Processing: {results['telemetry']['avg_telemetry_ms']:.2f}ms")
    print(f"   • Concurrent Throughput: {results['concurrent']['throughput_req_sec']:.1f} req/sec")
    print(f"   • Cache Performance: {results['optimization']['avg_cache_ms']:.2f}ms")
    print(f"   • Spatial Queries: {results['optimization']['avg_spatial_ms']:.2f}ms")
    
    print("\n🚀 Optimization Benefits:")
    
    # Calculate improvements
    if results['basic']['zones_ms'] < 50:
        print("   ✅ Zone queries are optimized (< 50ms)")
    else:
        print("   ⚠️ Zone queries could be optimized further")
    
    if results['telemetry']['avg_telemetry_ms'] < 100:
        print("   ✅ Telemetry processing is optimized (< 100ms)")
    else:
        print("   ⚠️ Telemetry processing could be optimized further")
    
    if results['concurrent']['throughput_req_sec'] > 100:
        print("   ✅ High throughput achieved (> 100 req/sec)")
    else:
        print("   ⚠️ Throughput could be improved")
    
    if results['optimization']['avg_cache_ms'] < results['basic']['zones_ms'] * 0.5:
        print("   ✅ Cache is providing significant performance boost")
    else:
        print("   ⚠️ Cache optimization could be improved")
    
    print("\n📈 Recommendations:")
    print("   • Monitor cache hit rates for optimal performance")
    print("   • Consider Redis for distributed caching")
    print("   • Implement database connection pooling")
    print("   • Add performance monitoring and alerting")
    print("   • Consider horizontal scaling for higher throughput")

def main():
    """Run comprehensive performance tests"""
    print("🌊 DeepSeaGuard Performance Test Suite")
    print("=" * 60)
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Run all tests
        basic_results = test_basic_performance()
        telemetry_results = test_telemetry_performance()
        concurrent_results = test_concurrent_performance()
        optimization_results = test_optimization_features()
        
        # Compile results
        all_results = {
            'basic': basic_results,
            'telemetry': telemetry_results,
            'concurrent': concurrent_results,
            'optimization': optimization_results
        }
        
        # Generate report
        generate_performance_report(all_results)
        
        print(f"\n✅ Performance test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        print("Make sure the DeepSeaGuard server is running on http://localhost:8000")

if __name__ == "__main__":
    main() 