Feature: Weather aggregation
  As a consumer of the Weather Aggregator API
  I want to fetch and query stored weather readings for a city
  So that I can see current conditions and how they changed over time

  Background:
    Given Open-Meteo knows the city "Bangalore" at latitude 12.97 and longitude 77.59

  Scenario: Fetching the weather for a city stores the reading
    Given Open-Meteo reports 22.4 degrees, wind 14.2 km/h and weather code 3 for "Bangalore"
    When I fetch the weather for "Bangalore"
    Then the response status is 201
    And the reading shows 22.4 degrees and wind 14.2 km/h described as "Overcast"
    And 1 reading is stored for "Bangalore"

  Scenario: Fetching again within the freshness window reuses the stored reading
    Given Open-Meteo reports 22.4 degrees, wind 14.2 km/h and weather code 3 for "Bangalore"
    When I fetch the weather for "Bangalore"
    And 2 minutes pass
    And I fetch the weather for "Bangalore"
    Then the response status is 200
    And Open-Meteo was only contacted for the first fetch
    And 1 reading is stored for "Bangalore"

  Scenario: Stored readings are listed with the most recent first
    Given Open-Meteo reports 10.0 degrees, wind 5.0 km/h and weather code 0 for "Bangalore"
    And Open-Meteo reports 12.5 degrees, wind 8.0 km/h and weather code 61 for "Bangalore"
    When I fetch the weather for "Bangalore"
    And 10 minutes pass
    And I fetch the weather for "Bangalore"
    And I request the stored readings for "Bangalore"
    Then the response status is 200
    And the readings have temperatures 12.5, 10.0 in that order

  Scenario: The latest reading is the most recently fetched one
    Given Open-Meteo reports 10.0 degrees, wind 5.0 km/h and weather code 0 for "Bangalore"
    And Open-Meteo reports 12.5 degrees, wind 8.0 km/h and weather code 61 for "Bangalore"
    When I fetch the weather for "Bangalore"
    And 10 minutes pass
    And I fetch the weather for "Bangalore"
    And I request the latest reading for "Bangalore"
    Then the response status is 200
    And the reading shows 12.5 degrees and wind 8.0 km/h described as "Rain: slight"

  Scenario: Asking for a city that does not exist
    Given Open-Meteo does not know the city "Atlantis"
    When I fetch the weather for "Atlantis"
    Then the response status is 404
    And 0 readings are stored for "Atlantis"

  Scenario: Open-Meteo is unavailable
    Given Open-Meteo is unavailable
    When I fetch the weather for "Bangalore"
    Then the response status is 502
    And 0 readings are stored for "Bangalore"
