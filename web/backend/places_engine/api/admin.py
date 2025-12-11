# pylint: disable=broad-exception-caught
"""
TripRaft Places Admin API

Admin endpoints for dataset management and monitoring.

Endpoints:
    GET  /api/admin/places/analysis       - Dataset analysis report
    GET  /api/admin/places/empty-files    - Files without data
    GET  /api/admin/places/incomplete     - Files with incomplete data
    GET  /api/admin/places/stats          - Summary statistics
    GET  /api/admin/places/by-country     - Stats grouped by country
    GET  /api/admin/places/file/<id>      - Details for specific file
    POST /api/admin/places/validate       - Run photo validation
    GET  /api/admin/places/pipeline       - Pipeline status
"""

import json
from flask import Blueprint, jsonify, request, current_app
from pathlib import Path

from ..pipeline.analyze_dataset import DatasetAnalyzer
from ..pipeline.validate_photos import PhotoValidator
from ..config import PlacesEngineConfig

# Create blueprint
admin_bp = Blueprint('places_admin', __name__, url_prefix='/api/admin/places')

# Get config
config = PlacesEngineConfig()


def _get_report_path() -> Path:
    """Get path to analysis report file."""
    return config.ENGINE_DIR / 'analysis_report.json'


@admin_bp.route('/analysis', methods=['GET'])
def get_dataset_analysis():
    """
    Get comprehensive analysis of the places dataset.
    
    Query params:
        refresh: Force re-analysis (default: false)
    
    Returns:
        JSON with complete dataset analysis
    """
    try:
        refresh = request.args.get('refresh', 'false').lower() == 'true'
        report_path = _get_report_path()
        
        # Return cached report if available
        if not refresh and report_path.exists():
            with open(report_path, 'r', encoding='utf-8') as f:
                report = json.load(f)
            return jsonify({
                'success': True,
                'cached': True,
                'data': report
            })
        
        # Run fresh analysis
        analyzer = DatasetAnalyzer(dataset_path=str(config.dataset_path))
        report = analyzer.run()
        
        # Save report
        analyzer.save_report(str(report_path))
        
        return jsonify({
            'success': True,
            'cached': False,
            'data': report
        })
        
    except Exception as e:
        current_app.logger.error(f"Dataset analysis error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/empty-files', methods=['GET'])
def get_empty_files():
    """
    Get list of files with no places data.
    These files need to be populated before upload.
    
    Returns:
        JSON with empty files list
    """
    try:
        report_path = _get_report_path()
        
        if not report_path.exists():
            return jsonify({
                'success': False,
                'error': 'No analysis report found. Run /api/admin/places/analysis?refresh=true first.'
            }), 404
        
        with open(report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        empty_files = [
            {
                'file_id': f['file_id'],
                'file_name': f['file_name'],
                'country': f['country'],
                'state': f['state'],
                'file_path': f['file_path']
            }
            for f in report.get('files', [])
            if f.get('places_count', 0) == 0
        ]
        
        return jsonify({
            'success': True,
            'count': len(empty_files),
            'files': empty_files
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/incomplete', methods=['GET'])
def get_incomplete_files():
    """
    Get list of files with incomplete place data.
    These files have places but are missing required fields.
    
    Returns:
        JSON with incomplete files and their issues
    """
    try:
        report_path = _get_report_path()
        
        if not report_path.exists():
            return jsonify({
                'success': False,
                'error': 'No analysis report found.'
            }), 404
        
        with open(report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        incomplete = [
            {
                'file_id': f['file_id'],
                'file_name': f['file_name'],
                'country': f['country'],
                'state': f['state'],
                'places_count': f['places_count'],
                'complete_places': f['complete_places'],
                'issues': f.get('issues', [])
            }
            for f in report.get('files', [])
            if f.get('places_count', 0) > 0 and f.get('complete_places', 0) < f.get('places_count', 0)
        ]
        
        return jsonify({
            'success': True,
            'count': len(incomplete),
            'files': incomplete
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/stats', methods=['GET'])
def get_dataset_stats():
    """
    Get summary statistics for the dataset.
    
    Returns:
        JSON with aggregated statistics
    """
    try:
        report_path = _get_report_path()
        
        if not report_path.exists():
            return jsonify({
                'success': False,
                'error': 'No analysis report found.'
            }), 404
        
        with open(report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        summary = report.get('summary', {})
        total_files = max(summary.get('total_files', 1), 1)
        
        return jsonify({
            'success': True,
            'stats': {
                'total_files': summary.get('total_files', 0),
                'complete_files': summary.get('complete_files', 0),
                'partial_files': summary.get('partial_files', 0),
                'empty_files': summary.get('empty_files', 0),
                'total_places': summary.get('total_places', 0),
                'complete_places': summary.get('complete_places', 0),
                'places_without_coords': summary.get('places_without_coords', 0),
                'invalid_photos': summary.get('invalid_photos', 0),
                'completion_rate': round(summary.get('complete_files', 0) / total_files * 100, 1),
                'generated_at': report.get('generated_at', 'Unknown')
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/by-country', methods=['GET'])
def get_stats_by_country():
    """
    Get dataset statistics grouped by country.
    
    Query params:
        country: Filter by specific country (optional)
    
    Returns:
        JSON with country-level statistics
    """
    try:
        country_filter = request.args.get('country', '').lower()
        report_path = _get_report_path()
        
        if not report_path.exists():
            return jsonify({
                'success': False,
                'error': 'No analysis report found.'
            }), 404
        
        with open(report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        by_country = report.get('by_country', {})
        
        if country_filter:
            matching = {
                k: v for k, v in by_country.items()
                if country_filter in k.lower()
            }
            return jsonify({
                'success': True,
                'countries': matching
            })
        
        # Sort by places count descending
        sorted_countries = dict(
            sorted(by_country.items(), key=lambda x: x[1].get('places', 0), reverse=True)
        )
        
        return jsonify({
            'success': True,
            'total_countries': len(sorted_countries),
            'countries': sorted_countries
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/file/<file_id>', methods=['GET'])
def get_file_details(file_id: str):
    """
    Get detailed analysis for a specific file by ID.
    
    Args:
        file_id: File identifier
    
    Returns:
        JSON with file details and issues
    """
    try:
        report_path = _get_report_path()
        
        if not report_path.exists():
            return jsonify({
                'success': False,
                'error': 'No analysis report found.'
            }), 404
        
        with open(report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        for file_info in report.get('files', []):
            if file_info.get('file_id') == file_id:
                return jsonify({
                    'success': True,
                    'file': file_info
                })
        
        return jsonify({
            'success': False,
            'error': f'File with ID {file_id} not found'
        }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/validate', methods=['POST'])
def validate_photos():
    """
    Run photo validation on the dataset.
    
    Body params:
        file_path: Specific file to validate (optional)
        fix: Apply fixes (default: false)
    
    Returns:
        JSON with validation results
    """
    try:
        data = request.get_json() or {}
        fix = data.get('fix', False)
        
        validator = PhotoValidator(dataset_path=str(config.dataset_path))
        result = validator.run(fix=fix)
        
        return jsonify({
            'success': True,
            'fix_mode': fix,
            'result': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/pipeline', methods=['GET'])
def get_pipeline_status():
    """
    Get current status of the data pipeline.
    
    Returns:
        JSON with pipeline stage status
    """
    try:
        report_path = _get_report_path()
        analysis_exists = report_path.exists()
        
        summary = {}
        if analysis_exists:
            with open(report_path, 'r', encoding='utf-8') as f:
                report = json.load(f)
                summary = report.get('summary', {})
        
        return jsonify({
            'success': True,
            'pipeline': {
                'analysis': {
                    'completed': analysis_exists,
                    'stats': summary if analysis_exists else None
                },
                'photo_validation': {
                    'completed': False,
                    'invalid_photos': summary.get('invalid_photos', 0)
                },
                'preparation': {
                    'completed': False
                },
                'upload': {
                    'completed': False,
                    'last_upload': None
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
