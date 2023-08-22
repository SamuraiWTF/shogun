#!/bin/bash

# Initialize peak memory usage variable for each container
declare -A peak_memory_usage

while true; do
  # Get the memory usage for all running containers
  docker_stats=$(docker stats --no-stream --format "{{.Name}} {{.MemUsage}}")

  # Process each line of the output
  while IFS= read -r line; do
    container_id=$(echo $line | awk '{print $1}')
    current_memory_usage=$(echo $line | awk '{print $2}' | sed 's/MiB//')

    # Compare with the peak memory usage and update if necessary
    if [[ ! ${peak_memory_usage[$container_id]} || $(echo "$current_memory_usage > ${peak_memory_usage[$container_id]}" | bc -l) -eq 1 ]]; then
      peak_memory_usage[$container_id]=$current_memory_usage
      echo "New peak memory usage for container $container_id: ${peak_memory_usage[$container_id]} MiB"
    fi
  done <<< "$docker_stats"

  # Wait for 1 second before checking again
  sleep 1
done