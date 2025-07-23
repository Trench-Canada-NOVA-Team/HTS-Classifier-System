from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger
import json

class AzureFeedbackTrainer:
    """
    Utility class for training and analytics using Azure Blob Storage feedback data.
    """
    
    def __init__(self, feedback_handler, pinecone_feedback_service=None):
        """
        Initialize the Azure feedback trainer.
        
        Args:
            feedback_handler: AzureFeedbackHandler instance with Azure capabilities
            pinecone_feedback_service: Optional Pinecone feedback service instance
        """
        self.feedback_handler = feedback_handler
        self.pinecone_feedback_service = pinecone_feedback_service
        
    def prepare_training_data(self, days: int = 30) -> Dict:
        """
        Prepare training data from Azure Blob Storage feedback for model improvement.
        
        Args:
            days: Number of days of feedback to analyze
            
        Returns:
            Dictionary with training preparation results
        """
        try:
            logger.info(f"Preparing training data from Azure Blob Storage for last {days} days...")
            
            # Get recent feedback data
            feedback_df = self.feedback_handler.get_recent_feedback(days=days)
            
            if feedback_df.empty:
                return {
                    'success': False,
                    'error': 'No feedback data available for training'
                }
            
            # Analyze the feedback data
            analysis = self._analyze_feedback_data(feedback_df)
            
            # Prepare training insights
            insights = self._generate_training_insights(feedback_df, analysis)
            
            result = {
                'success': True,
                'total_feedback_entries': len(feedback_df),
                'correction_entries': analysis['total_corrections'],
                'accuracy_before': analysis['accuracy_rate'],
                'insights': insights,
                'top_correction_patterns': analysis['top_patterns'],
                'problematic_chapters': analysis['problematic_chapters']
            }
            
            logger.info(f"Training data prepared from Azure: {result['total_feedback_entries']} entries analyzed")
            return result
            
        except Exception as e:
            logger.error(f"Error preparing training data from Azure: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _analyze_feedback_data(self, feedback_df: pd.DataFrame) -> Dict:
        """
        Analyze feedback data for training insights.
        
        Args:
            feedback_df: DataFrame with feedback data
            
        Returns:
            Dictionary with analysis results
        """
        try:
            analysis = {
                'total_entries': len(feedback_df),
                'total_corrections': 0,
                'accuracy_rate': 0,
                'top_patterns': [],
                'problematic_chapters': [],
                'chapter_performance': {}
            }
            
            if feedback_df.empty:
                return analysis
            
            # Calculate corrections
            corrections = feedback_df[feedback_df['predicted_code'] != feedback_df['correct_code']]
            analysis['total_corrections'] = len(corrections)
            
            # Calculate accuracy
            if len(feedback_df) > 0:
                analysis['accuracy_rate'] = (len(feedback_df) - len(corrections)) / len(feedback_df)
            
            # Analyze correction patterns by chapter
            chapter_stats = {}
            for _, row in corrections.iterrows():
                pred_chapter = str(row['predicted_code'])[:2]
                correct_chapter = str(row['correct_code'])[:2]
                
                if pred_chapter != correct_chapter:
                    pattern = f"{pred_chapter}->{correct_chapter}"
                    chapter_stats[pattern] = chapter_stats.get(pattern, 0) + 1
            
            # Get top patterns
            analysis['top_patterns'] = sorted(
                [(pattern, count) for pattern, count in chapter_stats.items()],
                key=lambda x: x[1], reverse=True
            )[:5]
            
            # Identify problematic chapters (chapters with high error rates)
            chapter_errors = {}
            for _, row in feedback_df.iterrows():
                pred_chapter = str(row['predicted_code'])[:2]
                if pred_chapter not in chapter_errors:
                    chapter_errors[pred_chapter] = {'total': 0, 'errors': 0}
                
                chapter_errors[pred_chapter]['total'] += 1
                if row['predicted_code'] != row['correct_code']:
                    chapter_errors[pred_chapter]['errors'] += 1
            
            # Calculate error rates
            for chapter, stats in chapter_errors.items():
                if stats['total'] >= 3:  # Only consider chapters with enough data
                    error_rate = stats['errors'] / stats['total']
                    if error_rate > 0.4:  # 40% error rate threshold
                        analysis['problematic_chapters'].append({
                            'chapter': chapter,
                            'error_rate': error_rate,
                            'total_predictions': stats['total']
                        })
            
            analysis['chapter_performance'] = chapter_errors
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing feedback data: {str(e)}")
            return {'total_entries': 0, 'total_corrections': 0, 'accuracy_rate': 0}
    
    def _generate_training_insights(self, feedback_df: pd.DataFrame, analysis: Dict) -> Dict:
        """
        Generate actionable insights from feedback analysis.
        
        Args:
            feedback_df: DataFrame with feedback data
            analysis: Analysis results
            
        Returns:
            Dictionary with training insights
        """
        try:
            insights = {
                'recommendations': [],
                'priority_areas': [],
                'data_quality': 'good'
            }
            
            # Generate recommendations based on analysis
            if analysis['accuracy_rate'] < 0.7:
                insights['recommendations'].append(
                    "Overall accuracy is below 70% - consider reviewing classification logic"
                )
                insights['data_quality'] = 'poor'
            elif analysis['accuracy_rate'] < 0.8:
                insights['recommendations'].append(
                    "Accuracy could be improved - focus on top correction patterns"
                )
                insights['data_quality'] = 'fair'
            
            # Identify priority areas from problematic chapters
            for chapter_info in analysis['problematic_chapters']:
                insights['priority_areas'].append({
                    'area': f"Chapter {chapter_info['chapter']}",
                    'issue': f"High error rate: {chapter_info['error_rate']:.1%}",
                    'priority': 'high' if chapter_info['error_rate'] > 0.6 else 'medium'
                })
            
            # Recommendations for top patterns
            for pattern, count in analysis['top_patterns'][:3]:
                insights['recommendations'].append(
                    f"Review classification logic for pattern {pattern} (occurred {count} times)"
                )
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating training insights: {str(e)}")
            return {'recommendations': [], 'priority_areas': []}

    def generate_feedback_report(self, days: int = 30, format: str = 'dict') -> Dict:
        """
        Generate comprehensive feedback report from Azure Blob Storage.
        
        Args:
            days: Number of days to include in report
            format: Report format ('dict', 'csv', 'json')
            
        Returns:
            Comprehensive feedback report
        """
        try:
            logger.info(f"Generating feedback report from Azure for last {days} days...")
            
            # Get feedback data and metrics
            feedback_df = self.feedback_handler.get_recent_feedback(days=days)
            quality_metrics = self.feedback_handler.get_feedback_quality_metrics(days=days) if hasattr(self.feedback_handler, 'get_feedback_quality_metrics') else {}
            correction_patterns = self.feedback_handler.get_correction_patterns(days=days) if hasattr(self.feedback_handler, 'get_correction_patterns') else {}
            
            report = {
                'report_generated': datetime.now().isoformat(),
                'period_days': days,
                'summary': {
                    'total_entries': len(feedback_df) if not feedback_df.empty else 0,
                    'total_corrections': quality_metrics.get('total_corrections', 0),
                    'correction_rate': quality_metrics.get('correction_rate', 0),
                    'data_freshness': quality_metrics.get('data_freshness'),
                    'storage_location': "Azure Blob Storage" if self.feedback_handler.azure_available else "Local"
                },
                'quality_metrics': quality_metrics,
                'correction_patterns': correction_patterns,
                'detailed_analysis': {}
            }
            
            if not feedback_df.empty:
                # Add detailed analysis
                analysis = self._analyze_feedback_data(feedback_df)
                report['detailed_analysis'] = analysis
                
                # Add training recommendations
                insights = self._generate_training_insights(feedback_df, analysis)
                report['training_insights'] = insights
            
            # Format output based on requested format
            if format == 'json':
                return {'report_json': json.dumps(report, indent=2)}
            elif format == 'csv':
                return self._export_to_csv(feedback_df, report)
            else:
                return report
                
        except Exception as e:
            logger.error(f"Error generating feedback report from Azure: {str(e)}")
            return {'error': str(e)}

    def _export_to_csv(self, feedback_df: pd.DataFrame, report: Dict) -> Dict:
        """
        Export feedback data and report to CSV format.
        
        Args:
            feedback_df: DataFrame with feedback data
            report: Report dictionary
            
        Returns:
            Dictionary with CSV export information
        """
        try:
            if feedback_df.empty:
                return {'csv_data': '', 'summary': report['summary']}
            
            # Convert DataFrame to CSV string
            csv_data = feedback_df.to_csv(index=False)
            
            return {
                'csv_data': csv_data,
                'summary': report['summary'],
                'export_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {str(e)}")
            return {'error': str(e)}
    
    def get_training_recommendations(self, days: int = 30) -> List[Dict]:
        """
        Get specific training recommendations based on feedback analysis.
        
        Args:
            days: Number of days of feedback to analyze
            
        Returns:
            List of training recommendations
        """
        try:
            feedback_df = self.feedback_handler.get_recent_feedback(days=days)
            
            if feedback_df.empty:
                return []
            
            analysis = self._analyze_feedback_data(feedback_df)
            insights = self._generate_training_insights(feedback_df, analysis)
            
            recommendations = []
            
            # Convert insights to structured recommendations
            for rec in insights['recommendations']:
                recommendations.append({
                    'type': 'general',
                    'priority': 'medium',
                    'description': rec,
                    'action_required': True
                })
            
            for area in insights['priority_areas']:
                recommendations.append({
                    'type': 'specific',
                    'priority': area['priority'],
                    'description': f"Focus on {area['area']}: {area['issue']}",
                    'action_required': True
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting training recommendations: {str(e)}")
            return []
    
    def get_pinecone_feedback_performance_metrics(self) -> Dict:
        """Get performance metrics for Pinecone feedback service."""
        try:
            if not hasattr(self, 'pinecone_feedback_service') or not self.pinecone_feedback_service:
                return {'pinecone_feedback_available': False}
            
            pinecone_stats = self.pinecone_feedback_service.get_feedback_stats()
            
            return {
                'pinecone_feedback_available': True,
                'pinecone_total_vectors': pinecone_stats.get('total_vectors', 0),
                'pinecone_corrections': pinecone_stats.get('total_corrections', 0),
                'pinecone_index_type': pinecone_stats.get('index_type', 'Unknown'),
                'pinecone_embedding_model': pinecone_stats.get('embedding_model', 'Unknown'),
                'pinecone_initialized': pinecone_stats.get('is_initialized', False),
                'pinecone_index_name': pinecone_stats.get('index_name', 'Unknown')
            }
            
        except Exception as e:
            logger.error(f"Error getting Pinecone feedback performance metrics: {str(e)}")
            return {'pinecone_feedback_available': False, 'error': str(e)}

