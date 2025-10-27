"""
Conference data processing services

Centralizes data processing logic used across views and serializers.
"""

from .utils import split_comma_values, split_semicolon_values


class PublicationDataService:
    """Service for processing publication-related data"""

    def process_publication_for_table(self, publication) -> dict:
        """Process a publication instance for table display

        Args:
            publication: Publication model instance

        Returns:
            Dictionary with processed data including split fields
        """
        return {
            "id": publication.id,
            "title": publication.title,
            "authors": publication.authors,
            "rating": publication.rating,
            "research_topic": publication.research_topic,
            "session": publication.session,
            "aff_unique": publication.aff_unique,
            "aff_country_unique": publication.aff_country_unique,
            "keywords": publication.keywords,
            "pdf_url": publication.pdf_url,
            "github": publication.github,
            "site": publication.site,
            "instance_year": publication.instance.year,
            "venue_name": publication.instance.venue.name,
            # Split fields
            "authors_list": split_comma_values(publication.authors),
            "countries_list": split_comma_values(publication.aff_country_unique),
            "keywords_list": split_semicolon_values(publication.keywords),
        }

    def process_publications_for_aggregation(self, publications) -> dict:
        """Process publications for KPI and chart calculations

        Args:
            publications: QuerySet or list of Publication instances

        Returns:
            Dictionary with aggregated data using split values
        """
        all_authors = []
        all_countries = []  # Changed from set to list to preserve duplicates for counting
        all_affiliations = []  # Changed from set to list to preserve duplicates for counting
        all_keywords = []

        for pub in publications:
            # Authors (comma-separated)
            if pub.authors:
                all_authors.extend(split_comma_values(pub.authors))

            # Countries (comma-separated) - preserve duplicates for counting
            if pub.aff_country_unique:
                countries = split_comma_values(pub.aff_country_unique)
                all_countries.extend(countries)

            # Affiliations (semicolon-separated) - preserve duplicates for counting
            if pub.aff_unique:
                affiliations = split_semicolon_values(pub.aff_unique)
                all_affiliations.extend(affiliations)

            # Keywords (semicolon-separated)
            if pub.keywords:
                keywords = split_semicolon_values(pub.keywords)
                all_keywords.extend(keywords)

        return {
            "unique_authors": len(set(all_authors)),
            "unique_countries": len(set(all_countries)),  # Count unique for KPIs
            "unique_affiliations": len(set(all_affiliations)),  # Count unique for KPIs
            "all_authors": all_authors,
            "all_countries": all_countries,  # Keep duplicates for chart counting
            "all_affiliations": all_affiliations,  # Keep duplicates for chart counting
            "all_keywords": all_keywords,
        }


# Singleton instance for easy import
publication_data_service = PublicationDataService()
