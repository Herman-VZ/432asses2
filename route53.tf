resource "aws_route53_record" "api" {
  zone_id = "Z02680423BHWEVRU2JZDQ"
  name    = "kh.asses3.cab432.com"
  type    = "A"

  alias {
    name                   = aws_lb.app_lb.dns_name
    zone_id                = aws_lb.app_lb.zone_id
    evaluate_target_health = true
  }
}

output "domain_name" {
  value = aws_route53_record.api.fqdn
}