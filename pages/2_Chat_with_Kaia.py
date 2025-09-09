# Enhanced Caribbean Cultural Heritage Explorer with Live Web Search
import streamlit as st
import json
import os
import re
import requests
from urllib.parse import urlparse, quote
import time
from datetime import datetime
import random

try:
    import speech_recognition as sr
    SPEECH_AVAILABLE = True
except ImportError:
    SPEECH_AVAILABLE = False
    st.warning("Speech recognition not available. Install speech_recognition package for voice features.")

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    st.error("Google Generative AI not available. Install google-generativeai package.")

import streamlit.components.v1 as components

# API Key Configuration - Users should replace with their own keys
GOOGLE_AI_API_KEY = "YOUR_GOOGLE_AI_API_KEY_HERE"  # Replace with your Google AI API key
SERPER_API_KEY = "YOUR_SERPER_API_KEY_HERE"  # Replace with your Serper API key for web search

if GENAI_AVAILABLE and GOOGLE_AI_API_KEY != "YOUR_GOOGLE_AI_API_KEY_HERE":
    genai.configure(api_key=GOOGLE_AI_API_KEY)

# Avatar URL
CARIBBEAN_AVATAR = "https://img.freepik.com/premium-photo/juneteenth-celebration_939336-931.jpg"

# Enhanced Caribbean Islands Data
CARIBBEAN_ISLANDS = {
    "Greater Antilles": ["Cuba", "Jamaica", "Haiti", "Dominican Republic", "Puerto Rico", "Cayman Islands"],
    "Lesser Antilles": {
        "Leeward Islands": ["Antigua and Barbuda", "Saint Kitts and Nevis", "Anguilla", 
                           "British Virgin Islands", "U.S. Virgin Islands", "Montserrat", 
                           "Guadeloupe", "Saint Martin", "Sint Maarten"],
        "Windward Islands": ["Dominica", "Saint Lucia", "Saint Vincent and the Grenadines", 
                           "Grenada", "Martinique", "Barbados"]
    },
    "Southern Caribbean": ["Trinidad and Tobago", "Aruba", "Curaçao", "Bonaire"],
    "Western Caribbean": ["Belize", "Bay Islands (Honduras)", "Roatan", "Utila", "Guanaja"],
    "Other Territories": ["Turks and Caicos", "Bahamas", "Bermuda"]
}

# Web Search Function using Serper API
def search_web_sources(query, num_results=8):
    """Search the web for sources related to the query using Serper API."""
    
    if SERPER_API_KEY == "YOUR_SERPER_API_KEY_HERE":
        return get_fallback_search_guidance(query)
    
    try:
        # Clean and enhance the search query
        enhanced_query = enhance_search_query(query)
        
        url = "https://google.serper.dev/search"
        payload = json.dumps({
            "q": enhanced_query,
            "num": num_results,
            "gl": "us"  # Geographic location
        })
        headers = {
            'X-API-KEY': SERPER_API_KEY,
            'Content-Type': 'application/json'
        }
        
        response = requests.request("POST", url, headers=headers, data=payload, timeout=10)
        
        if response.status_code == 200:
            search_results = response.json()
            return process_search_results(search_results, query)
        else:
            st.error(f"Search API error: {response.status_code}")
            return get_fallback_search_guidance(query)
            
    except Exception as e:
        st.error(f"Search error: {e}")
        return get_fallback_search_guidance(query)

def enhance_search_query(query):
    """Enhance the search query with Caribbean-specific terms."""
    query_lower = query.lower()
    
    # Add Caribbean context if not present
    if "caribbean" not in query_lower and "west indies" not in query_lower:
        # Detect if query is about specific island
        for region_islands in CARIBBEAN_ISLANDS.values():
            if isinstance(region_islands, list):
                for island in region_islands:
                    if island.lower() in query_lower:
                        return query  # Already has island context
            elif isinstance(region_islands, dict):
                for subregion_islands in region_islands.values():
                    for island in subregion_islands:
                        if island.lower() in query_lower:
                            return query  # Already has island context
        
        # Add Caribbean context
        query = f"{query} Caribbean"
    
    # Enhance with relevant terms based on query type
    if any(word in query_lower for word in ["statistics", "data", "census", "population"]):
        query += " official statistics government"
    elif any(word in query_lower for word in ["culture", "music", "art", "heritage"]):
        query += " cultural heritage ministry"
    elif any(word in query_lower for word in ["government", "policy", "official"]):
        query += " government official site"
    elif any(word in query_lower for word in ["academic", "research", "study"]):
        query += " academic research university"
    elif any(word in query_lower for word in ["economy", "development", "trade"]):
        query += " economic development bank"
    
    return query

def process_search_results(search_results, original_query):
    """Process and format search results."""
    sources = []
    
    # Process organic results
    if 'organic' in search_results:
        for result in search_results['organic'][:6]:
            source_info = {
                'title': result.get('title', 'Unknown Title'),
                'url': result.get('link', ''),
                'snippet': result.get('snippet', ''),
                'source_type': categorize_source(result.get('link', ''))
            }
            sources.append(source_info)
    
    # Process knowledge graph if available
    if 'knowledgeGraph' in search_results:
        kg = search_results['knowledgeGraph']
        if 'description' in kg:
            sources.insert(0, {
                'title': kg.get('title', 'Knowledge Graph'),
                'url': kg.get('descriptionLink', ''),
                'snippet': kg.get('description', ''),
                'source_type': 'knowledge'
            })
    
    # Process answer box if available
    if 'answerBox' in search_results:
        ab = search_results['answerBox']
        sources.insert(0, {
            'title': ab.get('title', 'Featured Answer'),
            'url': ab.get('link', ''),
            'snippet': ab.get('snippet', ab.get('answer', '')),
            'source_type': 'featured'
        })
    
    return sources

def categorize_source(url):
    """Categorize the source type based on URL."""
    if not url:
        return 'unknown'
    
    domain = urlparse(url).netloc.lower()
    
    # Government sources
    if any(tld in domain for tld in ['.gov', '.gob']) or 'government' in domain:
        return 'government'
    
    # Academic sources
    if '.edu' in domain or any(uni in domain for uni in ['university', 'uwi', 'academic']):
        return 'academic'
    
    # International organizations
    if any(org in domain for org in ['worldbank', 'un.org', 'unesco', 'undp', 'iadb']):
        return 'international'
    
    # Regional organizations
    if any(org in domain for org in ['caricom', 'oecs', 'caribank']):
        return 'regional'
    
    # Statistical offices
    if any(stat in domain for stat in ['statistics', 'census', 'statin']):
        return 'statistics'
    
    # News sources
    if any(news in domain for news in ['news', 'times', 'guardian', 'reuters', 'bbc']):
        return 'news'
    
    return 'other'

def get_fallback_search_guidance(query):
    """Provide search guidance when web search API is not available."""
    query_lower = query.lower()
    
    # Analyze query to provide targeted search suggestions
    suggestions = []
    
    # Government sources
    if any(word in query_lower for word in ["government", "official", "policy", "ministry"]):
        suggestions.extend([
            {
                'title': 'Search: Caribbean Government Official Sites',
                'url': '',
                'snippet': 'Try searching: "[Country name] government official site" or "[Country] ministry [topic]"',
                'source_type': 'search_guidance'
            },
            {
                'title': 'CARICOM Member States Directory',
                'url': 'https://caricom.org/member-states-and-associate-members/',
                'snippet': 'Official directory of CARICOM member states with government links.',
                'source_type': 'regional'
            }
        ])
    
    # Statistical data sources
    if any(word in query_lower for word in ["statistics", "data", "census", "numbers"]):
        suggestions.extend([
            {
                'title': 'World Bank Caribbean Data',
                'url': 'https://www.worldbank.org/en/region/lac/brief/caribbean',
                'snippet': 'Comprehensive economic and development data for Caribbean countries.',
                'source_type': 'international'
            },
            {
                'title': 'UN ECLAC Caribbean Statistics',
                'url': 'https://www.cepal.org/en/headquarters-and-offices/eclac-caribbean',
                'snippet': 'United Nations Economic Commission for Latin America and the Caribbean statistics.',
                'source_type': 'international'
            }
        ])
    
    # Cultural and heritage sources
    if any(word in query_lower for word in ["culture", "music", "art", "heritage", "festival"]):
        suggestions.extend([
            {
                'title': 'Search: Caribbean Cultural Organizations',
                'url': '',
                'snippet': 'Try: "[Country] cultural ministry" or "Caribbean [cultural topic] research"',
                'source_type': 'search_guidance'
            },
            {
                'title': 'CARICOM Culture Division',
                'url': 'https://caricom.org/our-work/human-and-social-development/culture/',
                'snippet': 'Regional cultural policies and initiatives across the Caribbean.',
                'source_type': 'regional'
            }
        ])
    
    # Academic sources
    if any(word in query_lower for word in ["research", "academic", "study", "journal"]):
        suggestions.extend([
            {
                'title': 'University of the West Indies',
                'url': 'https://www.uwi.edu/',
                'snippet': 'Leading Caribbean academic institution with extensive research resources.',
                'source_type': 'academic'
            },
            {
                'title': 'Search: Caribbean Academic Research',
                'url': '',
                'snippet': 'Try: "Caribbean studies [topic] academic" or "[topic] Caribbean research papers"',
                'source_type': 'search_guidance'
            }
        ])
    
    # Economic and development sources
    if any(word in query_lower for word in ["economy", "development", "trade", "business"]):
        suggestions.extend([
            {
                'title': 'Caribbean Development Bank',
                'url': 'https://www.caribank.org/',
                'snippet': 'Regional development bank focusing on Caribbean economic development.',
                'source_type': 'regional'
            },
            {
                'title': 'Inter-American Development Bank - Caribbean',
                'url': 'https://www.iadb.org/en/countries/caribbean/overview',
                'snippet': 'Development financing and economic analysis for the Caribbean region.',
                'source_type': 'international'
            }
        ])
    
    # Default suggestions if no specific category matches
    if not suggestions:
        suggestions = [
            {
                'title': 'CARICOM - Caribbean Community',
                'url': 'https://caricom.org/',
                'snippet': 'Official website of the Caribbean Community regional organization.',
                'source_type': 'regional'
            },
            {
                'title': 'Search Template for Your Query',
                'url': '',
                'snippet': f'Try searching: "{query} Caribbean official" or "{query} Caribbean research"',
                'source_type': 'search_guidance'
            }
        ]
    
    return suggestions[:6]

# Enhanced Response Function with Live Web Search
def get_enhanced_response_with_web_search(user_prompt, lang_code, selected_island=None):
    """Enhanced response function with live web search."""
    
    # Get web search results first
    search_results = search_web_sources(user_prompt)
    
    # Get AI response if available
    if not GENAI_AVAILABLE or GOOGLE_AI_API_KEY == "YOUR_GOOGLE_AI_API_KEY_HERE":
        ai_response = get_mock_response(user_prompt, lang_code)
    else:
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Include search results in the AI prompt for more informed responses
            search_context = "\n".join([
                f"Source: {result['title']}\nURL: {result['url']}\nContent: {result['snippet']}\n"
                for result in search_results[:3] if result['source_type'] != 'search_guidance'
            ])
            
            persona_prompt = f"""
            You are Kaia, a knowledgeable Caribbean cultural ambassador and academic expert.
            Use the provided web search results to give accurate, current information.
            
            Available search results:
            {search_context}
            
            Provide comprehensive answers that:
            1. Directly address the user's question using current information from search results
            2. Include relevant cultural and academic context
            3. Connect to broader Caribbean studies themes
            4. Reference the search results naturally in your response
            
            Always mention that current sources are provided separately.
            """

            island_context = f"\nFocus island: {selected_island}" if selected_island else ""

            full_prompt = f"""
            {persona_prompt}
            {island_context}
            
            User question in {lang_code}: '{user_prompt}'
            
            Provide a comprehensive answer in {lang_code}. Reference the search results naturally and mention that verified sources follow.
            """

            response = model.generate_content(full_prompt)
            ai_response = response.text if response.text else get_mock_response(user_prompt, lang_code)
            
        except Exception as e:
            st.error(f"AI API Error: {e}")
            ai_response = get_mock_response(user_prompt, lang_code)
    
    # Format the complete response
    full_response = ai_response + "\n\n"
    full_response += "### 🔍 Current Web Sources Found\n\n"
    
    # Group sources by type
    source_types = {
        'government': '🏛️ Government Sources',
        'academic': '🎓 Academic Sources', 
        'international': '🌍 International Organizations',
        'regional': '🤝 Regional Organizations',
        'statistics': '📊 Statistical Sources',
        'news': '📰 News Sources',
        'featured': '⭐ Featured Information',
        'knowledge': '📚 Knowledge Base',
        'search_guidance': '💡 Search Guidance',
        'other': '🔗 Additional Sources'
    }
    
    # Organize sources by type
    sources_by_type = {}
    for result in search_results:
        source_type = result['source_type']
        if source_type not in sources_by_type:
            sources_by_type[source_type] = []
        sources_by_type[source_type].append(result)
    
    # Display sources organized by type
    for source_type, sources in sources_by_type.items():
        if sources:
            full_response += f"\n**{source_types.get(source_type, '🔗 Sources')}:**\n\n"
            for i, source in enumerate(sources, 1):
                if source['url']:
                    full_response += f"{i}. **[{source['title']}]({source['url']})**\n"
                    full_response += f"   {source['snippet']}\n\n"
                else:
                    full_response += f"{i}. **{source['title']}**\n"
                    full_response += f"   {source['snippet']}\n\n"
    
    # Add search tips
    full_response += "\n### 💡 Additional Search Tips\n\n"
    full_response += "**For More Current Information:**\n"
    full_response += f"- Try searching: \"{user_prompt} Caribbean 2024\"\n"
    full_response += f"- Government sources: \"[Country] government {user_prompt.split()[0] if user_prompt.split() else 'official'}\"\n"
    full_response += f"- Academic sources: \"Caribbean studies {user_prompt} research\"\n\n"
    
    full_response += "**⚠️ Source Verification Tips:**\n"
    full_response += "- Check publication dates for currency\n"
    full_response += "- Prefer .gov, .edu, or established organization domains\n"
    full_response += "- Cross-reference information across multiple sources\n"
    full_response += "- Verify URLs are working before citing in research\n"
    
    return full_response

def get_mock_response(user_prompt, lang_code):
    """Enhanced mock response when AI is not available."""
    mock_responses = {
        "en": f"Thank you for asking about '{user_prompt}'. I've searched the web for current sources on this topic. While full AI analysis requires API configuration, I can provide you with the most current web sources and search guidance below.",
        "es": f"Gracias por preguntar sobre '{user_prompt}'. He buscado fuentes actuales en la web sobre este tema. Aunque el análisis completo de IA requiere configuración de API, puedo proporcionar fuentes web actuales y orientación de búsqueda.",
        "fr": f"Merci pour votre question sur '{user_prompt}'. J'ai cherché des sources actuelles sur le web concernant ce sujet. Bien que l'analyse IA complète nécessite une configuration API, je peux fournir des sources web actuelles et des conseils de recherche.",
        "nl": f"Bedankt voor uw vraag over '{user_prompt}'. Ik heb gezocht naar actuele webbronnen over dit onderwerp. Hoewel volledige AI-analyse API-configuratie vereist, kan ik actuele webbronnen en zoekbegeleiding verstrekken."
    }
    return mock_responses.get(lang_code, mock_responses["en"])

# Quick Source Finder with Web Search
def get_quick_sources_web_search(topic_type, island=None):
    """Get sources using web search for specific topics."""
    
    # Create search query based on topic and island
    if island and island != "All Caribbean Islands":
        search_query = f"{island} {topic_type}"
    else:
        search_query = f"Caribbean {topic_type}"
    
    # Add specific terms based on topic type
    topic_terms = {
        "government": "official government ministry policy",
        "statistics": "statistics data census bureau office",
        "academic": "university research academic studies",
        "culture": "cultural heritage ministry arts music",
        "regional": "CARICOM OECS regional organization",
        "environment": "environmental climate change adaptation"
    }
    
    if topic_type in topic_terms:
        search_query += " " + topic_terms[topic_type]
    
    return search_web_sources(search_query, num_results=6)

# Translation dictionary (keeping the same translations)
translations = {
    "en": {
        "title": "🌴 Caribbean Cultural Heritage & Academic Explorer with Web Search",
        "intro": "Welcome! I'm Kaia, your AI guide to Caribbean studies. I provide comprehensive answers with live web search results, current working sources, and academic guidance tailored to your questions.",
        "initial_bot_message": "Hello! I'm Kaia, your Caribbean studies expert. I help you explore Caribbean culture, development, and research by searching the web for current, relevant sources. I verify source quality and provide search guidance. What would you like to learn about today?",
        "input_placeholder": "Ask about Caribbean culture, development, or academic topics...",
        "sources_section": "Live Web Search Results & Sources"
    },
    "es": {
        "title": "🌴 Explorador Académico del Patrimonio Cultural del Caribe con Búsqueda Web",
        "intro": "¡Bienvenido/a! Soy Kaia, tu guía de IA para estudios caribeños. Proporciono respuestas con resultados de búsqueda web en vivo y fuentes actuales.",
        "initial_bot_message": "¡Hola! Soy Kaia, tu experta en estudios caribeños. Te ayudo explorando temas caribeños mediante búsqueda web de fuentes actuales y relevantes. ¿Qué te gustaría aprender hoy?",
        "input_placeholder": "Pregunta sobre cultura, desarrollo o temas académicos caribeños...",
        "sources_section": "Resultados de Búsqueda Web en Vivo y Fuentes"
    },
    "fr": {
        "title": "🌴 Explorateur Académique du Patrimoine Culturel des Caraïbes avec Recherche Web",
        "intro": "Bienvenue ! Je suis Kaia, votre guide IA pour les études caribéennes. Je fournis des réponses avec résultats de recherche web en direct.",
        "initial_bot_message": "Bonjour ! Je suis Kaia, votre experte en études caribéennes. J'aide en recherchant des sources actuelles et pertinentes sur le web. Qu'aimeriez-vous apprendre aujourd'hui ?",
        "input_placeholder": "Posez une question sur les sujets caribéens...",
        "sources_section": "Résultats de Recherche Web en Direct et Sources"
    },
    "nl": {
        "title": "🌴 Academische Caribische Cultureel Erfgoed Verkenner met Webzoekopdracht",
        "intro": "Welkom! Ik ben Kaia, uw AI-gids voor Caribische studies. Ik geef antwoorden met live webzoekresultaten en actuele bronnen.",
        "initial_bot_message": "Hallo! Ik ben Kaia, uw expert in Caribische studies. Ik help door het web te doorzoeken naar actuele, relevante bronnen. Wat wilt u vandaag leren?",
        "input_placeholder": "Vraag over Caribische onderwerpen...",
        "sources_section": "Live Webzoekresultaten en Bronnen"
    }
}

# Streamlit UI Setup
st.set_page_config(page_title="Caribbean Heritage Explorer - Web Search", layout="wide")

# Language selection
language_options = {"English": "en", "Español": "es", "Français": "fr", "Nederlands": "nl"}
selected_language_name = st.selectbox("Select Language / Idioma / Langue / Taal", list(language_options.keys()))

# Initialize session state
if "current_lang" not in st.session_state:
    st.session_state.current_lang = language_options[selected_language_name]

if st.session_state.current_lang != language_options[selected_language_name]:
    st.session_state.current_lang = language_options[selected_language_name]
    if "messages" in st.session_state:
        st.session_state.messages = [{"role": "bot", "content": translations[st.session_state.current_lang]["initial_bot_message"]}]

st.session_state.current_text = translations[st.session_state.current_lang]
current_text = st.session_state.current_text

# Main interface
st.title(current_text["title"])
st.markdown(current_text["intro"])

# API Key Status
col_api1, col_api2 = st.columns(2)
with col_api1:
    web_search_status = "✅ Enabled" if SERPER_API_KEY != "YOUR_SERPER_API_KEY_HERE" else "⚠️ Not Configured"
    st.markdown(f"**Web Search:** {web_search_status}")
with col_api2:
    ai_status = "✅ Enabled" if (GENAI_AVAILABLE and GOOGLE_AI_API_KEY != "YOUR_GOOGLE_AI_API_KEY_HERE") else "⚠️ Not Configured"
    st.markdown(f"**AI Analysis:** {ai_status}")

# Create layout columns
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    # Island selection
    st.header("🏝️ Island Focus")
    all_islands = ["All Caribbean Islands"]
    for region, islands in CARIBBEAN_ISLANDS.items():
        if isinstance(islands, list):
            all_islands.extend(islands)
        elif isinstance(islands, dict):
            for subregion, subislands in islands.items():
                all_islands.extend(subislands)
    
    all_islands = sorted(list(set(all_islands[1:])))
    all_islands.insert(0, "All Caribbean Islands")
    selected_island = st.selectbox("Choose focus:", all_islands)
    
    # Quick topic buttons with web search
    st.markdown("### 🎯 Quick Web Search")
    topic_buttons = [
        ("📊 Statistics & Data", "statistics"),
        ("🏛️ Government Info", "government"), 
        ("🎓 Academic Sources", "academic"),
        ("🎭 Cultural Heritage", "culture"),
        ("🤝 Regional Orgs", "regional"),
        ("🌿 Environment", "environment")
    ]
    
    for button_text, topic_key in topic_buttons:
        if st.button(button_text, key=f"topic_{topic_key}"):
            with st.spinner(f"Searching web for {topic_key} sources..."):
                sources = get_quick_sources_web_search(topic_key, selected_island)
                st.markdown("#### Web Search Results:")
                for i, source in enumerate(sources, 1):
                    if source['url']:
                        st.markdown(f"{i}. **[{source['title']}]({source['url']})**")
                        st.markdown(f"   *{source['snippet'][:100]}...*")
                    else:
                        st.markdown(f"{i}. **{source['title']}**")
                        st.markdown(f"   *{source['snippet'][:100]}...*")

with col2:
    # Chat interface
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "bot", "content": current_text["initial_bot_message"]}]

    # Display messages
    for message in st.session_state.messages:
        if message["role"] == "bot":
            with st.chat_message("assistant", avatar=CARIBBEAN_AVATAR):
                st.markdown(message["content"])
        else:
            with st.chat_message("user"):
                st.write(message["content"])

    # User input
    user_prompt = st.chat_input(current_text["input_placeholder"])

    # Quick search request buttons
    st.markdown("### 🔍 Quick Web Searches")
    col_q1, col_q2 = st.columns(2)
    
    with col_q1:
        if st.button("📈 Development Data", key="dev_data"):
            user_prompt = "Caribbean development statistics and economic indicators"
        if st.button("🎵 Music & Culture", key="music_culture"):
            user_prompt = "Caribbean music heritage and cultural traditions"
    
    with col_q2:
        if st.button("🏛️ Government Sites", key="gov_sites"):
            user_prompt = "Caribbean government official websites and ministries"
        if st.button("📚 Research Sources", key="research_sources"):
            user_prompt = "Caribbean academic research institutions and journals"

    # Process user input
    if user_prompt:
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        
        with st.chat_message("user"):
            st.write(user_prompt)
        
        with st.chat_message("assistant", avatar=CARIBBEAN_AVATAR):
            with st.spinner("Searching the web for current sources and generating response..."):
                bot_response = get_enhanced_response_with_web_search(
                    user_prompt, 
                    st.session_state.current_lang,
                    selected_island if selected_island != "All Caribbean Islands" else None
                )
                st.markdown(bot_response)
        
        st.session_state.messages.append({"role": "bot", "content": bot_response})

with col3:
    # Web search status and tools
    st.header("🔍 Web Search Tools")
    
    # Search status
    if SERPER_API_KEY != "YOUR_SERPER_API_KEY_HERE":
        st.success("✅ Web Search Active")
        st.markdown("Real-time web search enabled")
    else:
        st.warning("⚠️ Web Search Limited")
        st.markdown("Using fallback search guidance")
    
    st.markdown("### 🎯 Search Categories")
    search_categories = [
        ("Government", "Official government sites and policies"),
        ("Academic", "University research and scholarly articles"),
        ("Statistics", "Data and statistical offices"),
        ("Regional", "CARICOM, OECS, and regional organizations"),
        ("International", "UN, World Bank, development agencies"),
        ("Cultural", "Heritage, arts, and cultural institutions")
    ]
    
    for category, description in search_categories:
        with st.expander(f"🔍 {category}"):
            st.markdown(f"**{description}**")
            if st.button(f"Search {category}", key=f"search_{category.lower()}"):
                query = f"Caribbean {category.lower()}"
                if selected_island != "All Caribbean Islands":
                    query = f"{selected_island} {category.lower()}"
                
                with st.spinner(f"Searching for {category} sources..."):
                    results = search_web_sources(query, num_results=5)
                    for i, result in enumerate(results, 1):
                        if result['url']:
                            st.markdown(f"{i}. **[{result['title']}]({result['url']})**")
                        else:
                            st.markdown(f"{i}. **{result['title']}**")
                        st.markdown(f"   *{result['snippet'][:80]}...*")

# Enhanced footer with web search information
st.markdown("---")

# Information tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Web Search", "📚 Search Strategies", "✅ Source Verification", "🛠️ API Setup", "📖 Usage Guide"])

with tab1:
    st.markdown("""
    ### 🔍 Live Web Search Integration""")